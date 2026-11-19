"""Fastevo DRM for DarkFans videos (ported from the DarkFans scraper).

A DarkFans video's ``providerId`` is a Fastevo play token (PASETO
``v4.local``). Playing it takes four calls to Fastevo's API:

1. ``identities``: an identity claim for this "browser".
2. ``playback/initiate``: the play token plus an ephemeral P-256 key; the
   answer names the DASH manifest (with an access token) and wraps a session
   secret for that key (ClearKey v3).
3. ``identities/link1`` and ``link4``: tie the identity to the session.
4. ``licenses/ck``: an HMAC-signed request for the tracks' key ids; the answer
   is an AES-GCM sealed ``FCK3`` envelope of (kid, key) pairs.

Requests and answers of 1-3 are wrapped in AES-CBC with an RSA-OAEP key:
the web player's keys, read from its script at run time. The tracks are
CENC ``cbcs`` MP4s whose key ids are the ones in their ``tenc`` boxes; the
manifest's ``default_KID`` can name another key. The backend downloads them
like OnlyFans' Widevine streams, but this module decrypts them: mp4decrypt
(Bento4 1.6) turns these ``cbcs`` tracks into undecodable output, Shaka
Packager decrypts them, and every decrypted track is test-decoded.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import logging
import secrets
import shutil
import struct
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlencode, urljoin, urlparse

import aiohttp
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import HMAC, SHA256
from Crypto.Protocol.KDF import HKDF
from Crypto.PublicKey import ECC, RSA
from Crypto.Signature import pss
from Crypto.Util.Padding import pad, unpad

from ultima_scraper_api.apis.onlyfans.classes.only_drm import (
    FASTEVO_TOKEN_PREFIX,
    OnlyDRM,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.only_drm import DRMMedia

logger = logging.getLogger(__name__)

API_BASE = "https://api.fastevo.net"
WEBPLAY_BASE = "https://webplay.mp2.fastevo.net"
# The web player page; it names the current player script, which carries
# the player's RSA keys and version.
PLAYER_PAGE = f"{WEBPLAY_BASE}/release/index.html"
# The version sent when the player script names none.
CLIENT_VERSION = "1.0.430"
# How long keys read from the player script are reused.
PLAYER_KEYS_TTL = 6 * 60 * 60
BROWSER = {"name": "Chrome", "version": "143.0.0.0"}
LICENSE_PATH = "/service/api/v1/mediaprotection/licenses/ck"
TIMEOUT = aiohttp.ClientTimeout(total=60)
# Enough of a track's start to hold its moov/tenc boxes.
TRACK_HEAD_BYTES = 65536
# Seconds of a decrypted track test-decoded before it is kept.
DECODE_CHECK_SECONDS = 3


class FastevoError(RuntimeError):
    """Fastevo refused to play a video or to license its keys."""


# --- encoding -------------------------------------------------------------------------


def b64_decode(data: str) -> bytes:
    """Base64, url-safe or standard, padded or not."""
    data = data.replace("+", "-").replace("/", "_")
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def is_play_token(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(FASTEVO_TOKEN_PREFIX)


# --- the web player's keys -------------------------------------------------------------


@dataclass(frozen=True)
class PlayerKeys:
    """The RSA keys and version in Fastevo's web player script. They are read
    from Fastevo at run time rather than kept in this repository."""

    public_pem: str
    private_pem: str
    version: str


_JS_KEY = re.compile(
    r"""['"](-----BEGIN(?:\\x20| )(PUBLIC|PRIVATE)(?:\\x20| )KEY-----.*?"""
    r"""-----END(?:\\x20| )\2(?:\\x20| )KEY-----)['"]""",
    re.S,
)
_JS_VERSION = re.compile(r"(?:\\x22|\")version(?:\\x22|\"):(?:\\x22|\")(\d+\.\d+\.\d+)")
_PLAYER_SCRIPT = re.compile(r"""src=["']?([^"' >]*player\.[0-9a-f]+\.js)""")
_player_keys_cache: tuple[float, PlayerKeys] | None = None


def _js_string(literal: str) -> str:
    """A JS string literal's text: ``\\xNN`` escapes, then ``\\n``."""
    text = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), literal)
    return text.replace("\\n", "\n")


def player_script_url(page_html: str, page_url: str = PLAYER_PAGE) -> str | None:
    match = _PLAYER_SCRIPT.search(page_html)
    return urljoin(page_url, match.group(1)) if match else None


def parse_player_script(script: str) -> PlayerKeys:
    keys = {kind: _js_string(literal) for literal, kind in _JS_KEY.findall(script)}
    if "PUBLIC" not in keys or "PRIVATE" not in keys:
        raise FastevoError("Fastevo's player script holds no RSA key pair")
    version = _JS_VERSION.search(script)
    return PlayerKeys(
        public_pem=keys["PUBLIC"],
        private_pem=keys["PRIVATE"],
        version=version.group(1) if version else CLIENT_VERSION,
    )


async def load_player_keys(
    http: aiohttp.ClientSession, headers: dict[str, str]
) -> PlayerKeys:
    """The current player's keys, fetched once per ``PLAYER_KEYS_TTL``."""
    global _player_keys_cache
    if _player_keys_cache is not None and time.monotonic() < _player_keys_cache[0]:
        return _player_keys_cache[1]
    async with http.get(PLAYER_PAGE, headers=headers) as response:
        page = await response.text()
        if response.status != 200:
            raise FastevoError(f"Fastevo's player page answered {response.status}")
    script_url = player_script_url(page)
    if script_url is None:
        raise FastevoError("Fastevo's player page names no player script")
    async with http.get(script_url, headers=headers) as response:
        script = await response.text()
        if response.status != 200:
            raise FastevoError(f"Fastevo's player script answered {response.status}")
    keys = parse_player_script(script)
    _player_keys_cache = (time.monotonic() + PLAYER_KEYS_TTL, keys)
    return keys


# --- request wrapping (identities, playback) ------------------------------------------


class FastevoCrypto:
    """Fastevo's request/response envelope and request signature."""

    def __init__(self, keys: PlayerKeys) -> None:
        self._public_key = RSA.import_key(keys.public_pem)
        self._private_key = RSA.import_key(keys.private_pem)

    def encrypt(self, data: dict[str, Any]) -> dict[str, str]:
        """AES-256-CBC under a fresh key, the key sealed with RSA-OAEP."""
        aes_key = secrets.token_bytes(32)
        iv = secrets.token_bytes(16)
        ciphertext = AES.new(aes_key, AES.MODE_CBC, iv).encrypt(
            pad(json.dumps(data).encode(), AES.block_size)
        )
        sealed_key = PKCS1_OAEP.new(self._public_key, hashAlgo=SHA256).encrypt(aes_key)
        return {
            "e": base64.b64encode(ciphertext).decode(),
            "k": base64.b64encode(sealed_key).decode(),
            "i": base64.b64encode(iv).decode(),
        }

    def decrypt(self, e: str, k: str, i: str) -> dict[str, Any]:
        aes_key = PKCS1_OAEP.new(self._private_key, hashAlgo=SHA256).decrypt(b64_decode(k))
        plaintext = unpad(
            AES.new(aes_key, AES.MODE_CBC, b64_decode(i)).decrypt(b64_decode(e)),
            AES.block_size,
        )
        return cast(dict[str, Any], json.loads(plaintext.decode()))

    def open(self, data: Any) -> dict[str, Any]:
        """An answer, unwrapped when it is an ``{e, k, i}`` envelope."""
        if isinstance(data, dict) and all(key in data for key in ("e", "k", "i")):
            return self.decrypt(data["e"], data["k"], data["i"])
        return data if isinstance(data, dict) else {}

    def sign(self, method: str, url: str, body: str = "") -> str:
        """``x-signature``: RSA-PSS over ``timestamp|METHOD|path?query|body``."""
        timestamp = int(time.time() + 15)
        parsed = urlparse(url)
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        message = f"{timestamp}|{method}|{path}|{body}".encode()
        signature = pss.new(self._private_key, salt_bytes=32).sign(SHA256.new(message))
        return f"{base64.b64encode(signature).decode()}.{timestamp}"


# --- ClearKey v3 ------------------------------------------------------------------------


def unpack_fck3_envelope(payload: bytes) -> list[tuple[str, str]]:
    """A license envelope: ``FCK3``, version 3, type 1, count, (kid, key)*."""
    if len(payload) < 8 or payload[:4] != b"FCK3":
        raise ValueError(f"Invalid ClearKey envelope magic: {payload[:4]!r}")
    version, license_type = payload[4], payload[5]
    if version != 3 or license_type != 1:
        raise ValueError(f"Unsupported ClearKey envelope version: {version}.{license_type}")
    (count,) = struct.unpack(">H", payload[6:8])
    if len(payload) != 8 + count * 32:
        raise ValueError(
            f"ClearKey envelope payload length mismatch: expected {8 + count * 32}, got {len(payload)}"
        )
    return [
        (payload[at : at + 16].hex(), payload[at + 16 : at + 32].hex())
        for at in range(8, 8 + count * 32, 32)
    ]


class ClearKeySession:
    """The client side of one playback's ClearKey v3 key exchange."""

    def __init__(self) -> None:
        self._key = ECC.generate(curve="p256")
        point = self._key.pointQ
        self.public_jwk = {
            "crv": "P-256",
            "kty": "EC",
            "x": b64url(int(point.x).to_bytes(32, "big")),
            "y": b64url(int(point.y).to_bytes(32, "big")),
        }
        canonical_jwk = json.dumps(self.public_jwk, separators=(",", ":")).encode()
        self.thumbprint = b64url(SHA256.new(canonical_jwk).digest())
        self.license_path = LICENSE_PATH
        self.session_token = ""
        self.token_hash = ""
        self.request_mac_key = b""
        self.response_key = b""
        self.clock_offset_ms = 0.0
        self.configured = False

    def initiate_details(self) -> dict[str, Any]:
        return {"version": 3, "publicJwk": self.public_jwk}

    def configure(self, session: dict[str, Any], session_token: str) -> None:
        """Unwrap the session secret and derive the request and response keys."""
        server = session["serverPublicJwk"]
        server_point = ECC.construct(
            curve="p256",
            point_x=int.from_bytes(b64_decode(server["x"]), "big"),
            point_y=int.from_bytes(b64_decode(server["y"]), "big"),
        ).pointQ
        shared = int((server_point * self._key.d).x).to_bytes(32, "big")
        wrap_key = cast(
            bytes,
            HKDF(
                shared, 32, b64_decode(session["salt"]), SHA256,
                context=b"fastevo-clearkey-v3/session-secret-wrap",
            ),
        )
        cipher = AES.new(wrap_key, AES.MODE_GCM, nonce=b64_decode(session["iv"]))
        cipher.update(b"v3\n" + self.thumbprint.encode())
        secret = cipher.decrypt_and_verify(
            b64_decode(session["ciphertext"]), b64_decode(session["authenticationTag"])
        )
        token_hash = SHA256.new(session_token.encode()).digest()
        self.token_hash = b64url(token_hash)
        self.session_token = session_token
        self.license_path = session.get("licensePath") or LICENSE_PATH
        self.request_mac_key = cast(
            bytes,
            HKDF(secret, 32, token_hash, SHA256, context=b"fastevo-clearkey-v3/request-mac"),
        )
        self.response_key = cast(
            bytes,
            HKDF(
                secret, 32, token_hash, SHA256,
                context=b"fastevo-clearkey-v3/response-encryption",
            ),
        )
        self.configured = True

    def sync_clock(self, server_timestamp: Any) -> None:
        """License requests expire; time them by the server's clock."""
        try:
            if isinstance(server_timestamp, (int, float)):
                server_ms = float(server_timestamp)
            elif isinstance(server_timestamp, str) and server_timestamp.strip():
                server_ms = (
                    datetime.fromisoformat(server_timestamp.strip().replace("Z", "+00:00")).timestamp()
                    * 1000
                )
            else:
                return
        except (TypeError, ValueError, OverflowError):
            logger.warning("Invalid Fastevo server timestamp: %r", server_timestamp)
            return
        self.clock_offset_ms = server_ms - time.time() * 1000

    def license_request(self, kids: list[str]) -> tuple[str, dict[str, Any]]:
        """The canonical string the request MACs, and the request body."""
        if not self.configured:
            raise FastevoError("ClearKey session is not configured")
        kids_b64 = sorted(b64url(bytes.fromhex(kid.replace("-", ""))) for kid in kids)
        timestamp = int(time.time() * 1000 + self.clock_offset_ms)
        nonce = b64url(secrets.token_bytes(24))
        session_type = "temporary"
        canonical = "\n".join(
            [
                "v3", "POST", self.license_path, self.token_hash, str(timestamp),
                nonce, session_type, ",".join(kids_b64),
            ]
        )
        mac = HMAC.new(self.request_mac_key, digestmod=SHA256)
        mac.update(canonical.encode())
        body = {
            "version": 3,
            "timestamp": timestamp,
            "nonce": nonce,
            "type": session_type,
            "kids": kids_b64,
            "mac": b64url(mac.digest()),
        }
        return canonical, body

    def open_license(self, answer: dict[str, Any], canonical: str) -> dict[str, str]:
        """{kid hex: key hex} from a license answer."""
        cipher = AES.new(self.response_key, AES.MODE_GCM, nonce=b64_decode(answer["iv"]))
        cipher.update(canonical.encode())
        envelope = cipher.decrypt_and_verify(
            b64_decode(answer["ciphertext"]), b64_decode(answer["authenticationTag"])
        )
        return dict(unpack_fck3_envelope(envelope))


# --- manifest ---------------------------------------------------------------------------


@dataclass
class Track:
    kind: str  # "video" or "audio"
    url: str
    bandwidth: int = 0
    height: int = 0
    kid: str | None = None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _default_kid(element: ET.Element) -> str | None:
    for child in element:
        if _local(child.tag) != "ContentProtection":
            continue
        for name, value in child.attrib.items():
            if _local(name) == "default_KID" and value:
                return value.replace("-", "").lower()
    return None


def parse_manifest(text: str, manifest_url: str) -> list[Track]:
    """Every video and audio representation as one full-track download.

    Fastevo lists segment templates but also serves each representation
    whole: its ``BaseURL`` or ``video/<height>p/fullTrack.mp4`` /
    ``audio/fullTrack.m4a`` beside the manifest. Track links carry the
    manifest's access-token query.
    """
    root = ET.fromstring(text)
    parsed = urlparse(manifest_url)
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rsplit('/', 1)[0]}/"
    tracks: list[Track] = []
    for adaptation in root.iter():
        if _local(adaptation.tag) != "AdaptationSet":
            continue
        set_kid = _default_kid(adaptation)
        set_type = adaptation.get("contentType") or adaptation.get("mimeType", "")
        for rep in adaptation:
            if _local(rep.tag) != "Representation":
                continue
            mime = rep.get("mimeType") or set_type
            height = int(rep.get("height") or 0)
            kind = "video" if "video" in mime or height else "audio" if "audio" in mime else ""
            if not kind:
                continue
            base_url = next(
                (child.text for child in rep if _local(child.tag) == "BaseURL" and child.text),
                None,
            )
            if base_url:
                url = urljoin(base, base_url.strip())
            elif kind == "video":
                url = urljoin(base, f"video/{height}p/fullTrack.mp4")
            else:
                url = urljoin(base, "audio/fullTrack.m4a")
            if parsed.query and "?" not in url:
                url = f"{url}?{parsed.query}"
            tracks.append(
                Track(
                    kind=kind,
                    url=url,
                    bandwidth=int(rep.get("bandwidth") or 0),
                    height=height,
                    kid=_default_kid(rep) or set_kid,
                )
            )
    return tracks


def best_tracks(tracks: list[Track]) -> tuple[Track | None, Track | None]:
    videos = [track for track in tracks if track.kind == "video"]
    audios = [track for track in tracks if track.kind == "audio"]
    video = max(videos, key=lambda track: (track.height, track.bandwidth), default=None)
    audio = max(audios, key=lambda track: track.bandwidth, default=None)
    return video, audio


def track_kid(head: bytes) -> str | None:
    """The default key id in an MP4's ``tenc`` box."""
    at = head.find(b"tenc")
    if at == -1 or at + 28 > len(head):
        return None
    # size(4) 'tenc'(4) version/flags(4) reserved/pattern(2) protected(1) iv size(1) KID(16)
    return head[at + 12 : at + 28].hex()


def manifest_link(answer: dict[str, Any]) -> str | None:
    """The manifest a playback answer names, with its access token."""
    data = answer.get("playbackData") if isinstance(answer.get("playbackData"), dict) else answer
    url = data.get("mediaPlaylistUrl") or data.get("manifestUrl") or data.get("url")
    details = data.get("mediaPlaylistAccessTokenDetails") or {}
    params = details.get("queryParams") if isinstance(details, dict) else None
    if url and params:
        url = f"{url}{'&' if '?' in url else '?'}{urlencode(params)}"
    return url


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# --- the DRM module -----------------------------------------------------------------------


class FastevoDRM(OnlyDRM):
    """DarkFans' ``drm``: resolves a Fastevo video to its tracks and keys,
    and decrypts them with Shaka Packager. Merging is OnlyDRM's (ffmpeg);
    there is no Widevine device.
    """

    # The backend must hand these streams to decrypt_file_async: neither its
    # one-pass ffmpeg decrypt nor an mp4decrypt-only peer can decrypt them.
    decrypts_own_streams = True

    def __init__(
        self,
        authed: Any,
        *,
        media_formatter: Any = None,
        auto_start_workers: bool = True,
        max_workers: int | None = None,
    ) -> None:
        self._setup_media_tools(
            authed,
            media_formatter=media_formatter,
            auto_start_workers=auto_start_workers,
            max_workers=max_workers,
        )
        shaka = shutil.which("shaka-packager")
        if shaka is None:
            raise FileNotFoundError(
                "shaka-packager not found in PATH; it decrypts Fastevo's cbcs tracks: "
                "https://github.com/shaka-project/shaka-packager/releases"
            )
        self.shaka_filepath = Path(shaka)
        self.session_id = None
        self._crypto: FastevoCrypto | None = None
        self.client_version = CLIENT_VERSION

    @property
    def crypto(self) -> FastevoCrypto:
        if self._crypto is None:
            raise FastevoError("Fastevo's player keys are not loaded")
        return self._crypto

    @crypto.setter
    def crypto(self, crypto: FastevoCrypto) -> None:
        self._crypto = crypto

    def _headers(self) -> dict[str, str]:
        details = getattr(self.authed, "auth_details", None)
        user_agent = getattr(details, "user_agent", None) or ""
        return {
            "accept": "*/*",
            "origin": WEBPLAY_BASE,
            "referer": f"{WEBPLAY_BASE}/",
            "user-agent": user_agent,
        }

    async def _identity(self, http: aiohttp.ClientSession) -> str:
        url = f"{API_BASE}/service/api/v1/mediaprotection/identities"
        async with http.get(url, headers=self._headers()) as response:
            answer = self.crypto.open(await response.json(content_type=None))
        return str(answer.get("etagIdentityClaim") or answer.get("token") or "")

    async def _link(
        self, http: aiohttp.ClientSession, endpoint: str, session_token: str, fields: dict[str, Any]
    ) -> None:
        url = f"{API_BASE}/service/api/v1/mediaprotection/identities/{endpoint}"
        nonce = secrets.token_hex(16)
        body = json.dumps(
            self.crypto.encrypt(
                {**fields, "playbackSessionExchangeToken": session_token, "nonce": nonce}
            )
        )
        headers = {
            **self._headers(),
            "content-type": "application/json",
            "authorization": session_token,
            "x-signature": self.crypto.sign("POST", url, body),
        }
        try:
            async with http.post(url, headers=headers, data=body) as response:
                if response.status != 200:
                    logger.debug("Fastevo %s answered %s", endpoint, response.status)
        except aiohttp.ClientError as exc:
            logger.debug("Fastevo %s failed: %s", endpoint, exc)

    async def _initiate(
        self, http: aiohttp.ClientSession, token: str, session: ClearKeySession, identity: str
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "nonce": secrets.token_hex(16),
            "playTokenHash": _sha256(token),
            "supportedDRMSystems": ["org.w3.clearkey"],
            "clientVersion": self.client_version,
            "clientDetails": {
                "device": {"model": "Linux"},
                "os": {"name": "Linux", "version": ""},
                "browser": dict(BROWSER),
            },
            "device": "Linux",
            "operatingSystem": "Linux",
            "clearKeySession": session.initiate_details(),
        }
        if identity:
            payload["storageBasedIdentityClaim"] = identity
        url = f"{API_BASE}/service/api/v1/mediaprotection/playback/initiate"
        headers = {**self._headers(), "authorization": token, "content-type": "application/json"}
        async with http.post(url, headers=headers, json=self.crypto.encrypt(payload)) as response:
            raw = await response.json(content_type=None)
            if response.status >= 400:
                raise FastevoError(f"Fastevo refused playback ({response.status}): {raw}")
        return self.crypto.open(raw)

    async def _track_kid(self, http: aiohttp.ClientSession, url: str) -> str | None:
        headers = {**self._headers(), "range": f"bytes=0-{TRACK_HEAD_BYTES - 1}"}
        async with http.get(url, headers=headers) as response:
            if response.status not in (200, 206):
                return None
            return track_kid(await response.content.read(TRACK_HEAD_BYTES))

    async def _license(
        self, http: aiohttp.ClientSession, session: ClearKeySession, kids: list[str]
    ) -> dict[str, str]:
        canonical, body = session.license_request(kids)
        headers = {
            **self._headers(),
            "authorization": session.session_token,
            "content-type": "application/json",
        }
        # The player sends compact JSON; the MAC covers the canonical string.
        data = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
        async with http.post(f"{API_BASE}{session.license_path}", headers=headers, data=data) as response:
            answer = await response.json(content_type=None)
            if response.status != 200:
                raise FastevoError(f"Fastevo refused the license ({response.status}): {answer}")
        return session.open_license(answer, canonical)

    async def resolve_drm(self, drm_media: DRMMedia) -> tuple[str | None, str | None, str]:
        """(video track, audio track, ``KID:KEY`` pairs) for a Fastevo video."""
        token = str(drm_media.signature or "")
        if not is_play_token(token):
            raise FastevoError(f"Media {drm_media.media_id} has no Fastevo play token")
        session = ClearKeySession()
        async with aiohttp.ClientSession(timeout=TIMEOUT) as http:
            keys = await load_player_keys(http, self._headers())
            self.crypto = FastevoCrypto(keys)
            self.client_version = keys.version
            identity = await self._identity(http)
            answer = await self._initiate(http, token, session, identity)
            playback = answer.get("playbackData") if isinstance(answer.get("playbackData"), dict) else {}
            session_token = str(
                playback.get("playbackSessionExchangesToken")
                or answer.get("playbackSessionExchangesToken")
                or ""
            )
            if not session_token:
                raise FastevoError(f"Fastevo started no playback session for media {drm_media.media_id}")
            if identity:
                await self._link(http, "link1", session_token, {"etagIdentityClaim": identity})
                await self._link(http, "link4", session_token, {"ips": []})
            clear_key = playback.get("clearKeySession")
            if not isinstance(clear_key, dict):
                raise FastevoError("Fastevo offered no ClearKey session")
            if answer.get("currentTimestamp") is not None:
                session.sync_clock(answer["currentTimestamp"])
            session.configure(clear_key, session_token)

            manifest = manifest_link(answer)
            if not manifest:
                raise FastevoError(f"Fastevo named no manifest for media {drm_media.media_id}")
            async with http.get(manifest, headers=self._headers()) as response:
                if response.status != 200:
                    raise FastevoError(f"Fastevo manifest answered {response.status}")
                text = await response.text()
            video, audio = best_tracks(parse_manifest(text, manifest))
            if video is None:
                raise FastevoError(f"Fastevo manifest of media {drm_media.media_id} has no video")
            tracks = [track for track in (video, audio) if track is not None]
            for track in tracks:
                # The track's own tenc box names its key; the manifest's
                # default_KID can be another one.
                track.kid = await self._track_kid(http, track.url) or track.kid
            kids = sorted({track.kid for track in tracks if track.kid})
            if not kids:
                raise FastevoError(f"No key ids found in media {drm_media.media_id}'s tracks")
            keys = await self._license(http, session, kids)
        missing = [kid for kid in kids if kid not in keys]
        if missing:
            raise FastevoError(f"Fastevo licensed no key for {', '.join(missing)}")
        drm_media.video_url = video.url
        drm_media.audio_url = audio.url if audio is not None else None
        # One pair per key id; mp4decrypt picks each track's.
        key = " ".join(f"{kid}:{keys[kid]}" for kid in kids)
        return drm_media.video_url, drm_media.audio_url, key

    async def _track_kind(self, filepath: Path) -> str | None:
        """"video" or "audio" by the encrypted sample entry (None if clear)."""
        seen = {"overlap": b"", "kind": None}

        def consume(chunk: bytes) -> None:
            if seen["kind"] is None:
                chunk = seen["overlap"] + chunk
                seen["kind"] = "video" if b"encv" in chunk else "audio" if b"enca" in chunk else None
                seen["overlap"] = chunk[-3:]

        result = await self.media_formatter.run_process(
            [str(self.mp4dump_filepath), str(filepath)], stdout_consumer=consume
        )
        if result.returncode:
            raise RuntimeError(f"mp4dump failed: {result.stderr.decode(errors='replace')}")
        return cast(str | None, seen["kind"])

    async def _decodes(self, filepath: Path) -> str | None:
        """None when the start of ``filepath`` decodes cleanly, else why not."""
        result = await self.media_formatter.run_process(
            [
                "ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(filepath),
                "-t", str(DECODE_CHECK_SECONDS), "-f", "null", "-",
            ]
        )
        errors = result.stderr.decode(errors="replace").strip()
        if result.returncode or errors:
            return errors[-300:] or f"ffmpeg exited {result.returncode}"
        return None

    async def decrypt_file_async(
        self, filepath: Path, key: str, temp_output_path: Path | None = None
    ) -> Path:
        """Decrypt one track with Shaka Packager and test-decode it."""
        output, temporary = self._decryption_paths(filepath, temp_output_path)
        kind = await self._track_kind(filepath)
        if kind is None:
            return output if output.exists() else filepath
        labels = ",".join(
            f"label=k{index}:key_id={pair.split(':')[0]}:key={pair.split(':')[1]}"
            for index, pair in enumerate(key.split())
        )
        temporary.unlink(missing_ok=True)
        try:
            result = await self.media_formatter.run_process(
                [
                    str(self.shaka_filepath),
                    f"in={filepath},stream={kind},output={temporary}",
                    "--enable_raw_key_decryption",
                    "--keys",
                    labels,
                ]
            )
            if result.returncode:
                stderr = result.stderr.decode(errors="replace")
                for pair in key.split():
                    stderr = stderr.replace(pair.split(":")[-1], "[key]")
                raise RuntimeError(f"shaka-packager failed: {stderr[-500:]}")
            problem = await self._decodes(temporary)
            if problem:
                raise RuntimeError(
                    f"Decrypted {kind} of {filepath.name} does not decode "
                    f"(wrong key or damaged track): {problem}"
                )
            return self._commit_decryption(filepath, temporary, output)
        finally:
            temporary.unlink(missing_ok=True)

    def decrypt_file(self, filepath: Path, key: str, temp_output_path: Path | None = None) -> Path:
        raise NotImplementedError("Fastevo tracks are decrypted with decrypt_file_async")

    async def shutdown(self) -> None:
        await self.media_formatter.shutdown()


def media_request_headers(url: str) -> dict[str, str]:
    """Fastevo's media hosts serve its web player's origin."""
    host = (urlparse(url).hostname or "").lower()
    if host == "fastevo.net" or host.endswith(".fastevo.net"):
        return {"Origin": WEBPLAY_BASE, "Referer": f"{WEBPLAY_BASE}/"}
    return {}


__all__ = [
    "ClearKeySession",
    "FastevoCrypto",
    "FastevoDRM",
    "FastevoError",
    "Track",
    "best_tracks",
    "is_play_token",
    "manifest_link",
    "media_request_headers",
    "parse_manifest",
    "track_kid",
    "unpack_fck3_envelope",
]
