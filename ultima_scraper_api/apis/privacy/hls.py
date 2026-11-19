"""Privacy videos: AES-128 HLS where every request carries a file token.

What the site's player does (privacy-web-mediahub, checked live 2026-11-17):

1. POST ``/mediavideotoken/generate`` ``{"file_id": <first path segment>}``
   returns ``{"content": <token>}``.
2. Every request for the master playlist, the variant playlist, the AES key
   (on keyaes.privacy.com.br) and each ``.ts`` segment sends the headers
   ``content: <token>`` and ``x-content-uri: <last path segment>``. Without
   them the CDN answers 423.
3. Segments are AES-128-CBC (``#EXT-X-KEY:METHOD=AES-128``), the IV being the
   tag's ``IV`` or the segment's media sequence number, as HLS specifies.

``download_video`` writes the decrypted transport stream; ``save_video``
also remuxes it into an .mp4 (``ffmpeg -c copy``) when the destination asks
for one.
"""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

from Crypto.Cipher import AES

from ultima_scraper_api.apis.privacy.urls import (
    STANDARD_URL,
    APIRoutes,
    video_file_id,
    video_request_headers,
)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
LOCKED = 423  # what the CDN answers a missing or expired token

# (url, headers) -> (status, body)
Fetch = Callable[[str, dict[str, str]], Awaitable[tuple[int, bytes]]]
# file_id -> token
TokenSource = Callable[[str], Awaitable[str | None]]


class HlsError(RuntimeError):
    pass


@dataclass
class Key:
    method: str
    uri: str | None = None
    iv: bytes | None = None


@dataclass
class Playlist:
    variants: list[tuple[int, str]] = field(default_factory=list)  # (bandwidth, url)
    segments: list[tuple[str, int, Key | None]] = field(default_factory=list)


def _attributes(line: str) -> dict[str, str]:
    """``#TAG:A=1,B="x,y"`` -> {"A": "1", "B": "x,y"} (quoted commas kept)."""
    values: dict[str, str] = {}
    body = line.split(":", 1)[1] if ":" in line else ""
    key, value, quoted, reading_key = "", "", False, True
    for char in body + ",":
        if reading_key:
            if char == "=":
                reading_key = False
            elif char != ",":
                key += char
        elif char == '"':
            quoted = not quoted
        elif char == "," and not quoted:
            values[key.strip()] = value
            key, value, reading_key = "", "", True
        else:
            value += char
    return values


def parse_playlist(text: str, base_url: str) -> Playlist:
    playlist = Playlist()
    sequence = 0
    key: Key | None = None
    bandwidth: int | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            sequence = int(line.split(":", 1)[1])
        elif line.startswith("#EXT-X-KEY:"):
            attrs = _attributes(line)
            method = attrs.get("METHOD", "NONE")
            iv = attrs.get("IV")
            key = None if method == "NONE" else Key(
                method,
                urljoin(base_url, attrs["URI"]) if attrs.get("URI") else None,
                bytes.fromhex(iv[2:] if iv.lower().startswith("0x") else iv) if iv else None,
            )
        elif line.startswith("#EXT-X-STREAM-INF:"):
            bandwidth = int(_attributes(line).get("BANDWIDTH", "0"))
        elif not line.startswith("#"):
            url = urljoin(base_url, line)
            if bandwidth is not None:
                playlist.variants.append((bandwidth, url))
                bandwidth = None
            else:
                playlist.segments.append((url, sequence, key))
                sequence += 1
    return playlist


def decrypt_segment(data: bytes, key: bytes, iv: bytes) -> bytes:
    plain = AES.new(key, AES.MODE_CBC, iv).decrypt(data)
    pad = plain[-1] if plain else 0
    # PKCS#7, as HLS AES-128 specifies; leave data alone if the padding is off.
    if 0 < pad <= 16 and plain.endswith(bytes([pad]) * pad):
        plain = plain[:-pad]
    return plain


def segment_iv(key: Key, sequence: int) -> bytes:
    return key.iv if key.iv is not None else sequence.to_bytes(16, "big")


def _headers(url: str, token: str) -> dict[str, str]:
    return {
        "user-agent": USER_AGENT,
        "origin": STANDARD_URL,
        "referer": f"{STANDARD_URL}/",
        **video_request_headers(url, token),
    }


async def iter_video(
    playlist_url: str, fetch: Fetch, token_source: TokenSource
) -> AsyncGenerator[bytes, None]:
    """Yield the decrypted segments of a Privacy video, best quality first chosen.

    A 423 (token expired mid-download) gets one fresh token and a retry.
    """
    file_id = video_file_id(playlist_url)
    token = await token_source(file_id)
    if not token:
        raise HlsError("No video token (is the account allowed to view it?)")

    async def get(url: str) -> bytes:
        nonlocal token
        status, body = await fetch(url, _headers(url, token or ""))
        if status == LOCKED:
            token = await token_source(file_id)
            status, body = await fetch(url, _headers(url, token or ""))
        if status != 200:
            raise HlsError(f"HTTP {status} for {url.rsplit('/', 1)[-1]}")
        return body

    master = parse_playlist((await get(playlist_url)).decode(), playlist_url)
    media_url = max(master.variants)[1] if master.variants else playlist_url
    media = (
        master
        if media_url == playlist_url
        else parse_playlist((await get(media_url)).decode(), media_url)
    )
    if not media.segments:
        raise HlsError("Playlist has no segments")
    keys: dict[str, bytes] = {}
    for url, sequence, key in media.segments:
        data = await get(url)
        if key is None:
            yield data
            continue
        if key.method != "AES-128" or not key.uri:
            raise HlsError(f"Unsupported HLS encryption {key.method}")
        if key.uri not in keys:
            keys[key.uri] = await get(key.uri)
        yield decrypt_segment(data, keys[key.uri], segment_iv(key, sequence))


async def download_video(authed: Any, playlist_url: str, destination: Path) -> Path:
    """Write a Privacy video's decrypted transport stream to ``destination``."""
    requester = authed.get_requester()
    session = requester.active_session

    async def fetch(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        async with session.get(url, headers=headers) as response:
            return response.status, await response.read()

    async def token_source(file_id: str) -> str | None:
        response = await requester.request(
            APIRoutes().video_token(), "POST", json={"file_id": file_id}
        )
        if response is None or response.status != 200:
            return None
        body = await response.json()
        return body.get("content") if isinstance(body, dict) else None

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    with partial.open("wb") as out:
        async for chunk in iter_video(playlist_url, fetch, token_source):
            out.write(chunk)
    partial.replace(destination)
    return destination


def is_video_playlist(url: str | None) -> bool:
    """True for a Privacy video (an HLS playlist), False for direct files."""
    return bool(url) and urlsplit(str(url)).path.endswith(".m3u8")


async def remux_to_mp4(source: Path, destination: Path) -> Path:
    """Copy a transport stream's tracks into an .mp4 (no re-encode)."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise HlsError("ffmpeg is needed to save Privacy videos as .mp4")
    partial = destination.with_name(destination.name + ".part")
    process = await asyncio.create_subprocess_exec(
        ffmpeg, "-y", "-loglevel", "error", "-i", str(source),
        "-c", "copy", "-bsf:a", "aac_adtstoasc", "-f", "mp4", str(partial),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        partial.unlink(missing_ok=True)
        raise HlsError(f"ffmpeg could not remux the video: {stderr.decode(errors='replace')[-300:]}")
    partial.replace(destination)
    return destination


async def save_video(authed: Any, playlist_url: str, destination: Path) -> Path:
    """Save a Privacy video at ``destination``: the transport stream itself,
    or for an .mp4 destination the stream remuxed into it."""
    if destination.suffix.lower() != ".mp4":
        return await download_video(authed, playlist_url, destination)
    stream = destination.with_name(destination.stem + ".ts")
    try:
        await download_video(authed, playlist_url, stream)
        return await remux_to_mp4(stream, destination)
    finally:
        stream.unlink(missing_ok=True)
