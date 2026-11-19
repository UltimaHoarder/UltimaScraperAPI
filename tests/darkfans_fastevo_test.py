"""Fastevo DRM (DarkFans videos): the key exchange, manifest and keys,
played against a stand-in for Fastevo's server."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF
from Crypto.PublicKey import ECC, RSA
from Crypto.Util.Padding import pad

from ultima_scraper_api.apis.darkfans import fastevo
from ultima_scraper_api.apis.onlyfans.classes.only_drm import (
    DRMMedia,
    mp4decrypt_key_arguments,
)

VIDEO_KID = "00112233445566778899aabb00000001"
AUDIO_KID = "00112233445566778899aabb00000002"
KEYS = {VIDEO_KID: "0f0e0d0c0b0a09080706050403020100", AUDIO_KID: "11" * 16}
HOST = "https://media.fastevo.test"
VIDEO_ID = "65f0c0ffee00000000000001"

MANIFEST = f"""<?xml version="1.0"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" xmlns:cenc="urn:mpeg:cenc:2013">
  <Period>
    <AdaptationSet contentType="video" mimeType="video/mp4">
      <ContentProtection schemeIdUri="urn:mpeg:dash:mp4protection:2011" value="cbcs"
        cenc:default_KID="00112233-4455-6677-8899-aabb000000ff"/>
      <Representation id="v1" bandwidth="900000" width="854" height="480"/>
      <Representation id="v2" bandwidth="3000000" width="1920" height="1080"/>
    </AdaptationSet>
    <AdaptationSet contentType="audio" mimeType="audio/mp4">
      <Representation id="a1" bandwidth="128000"/>
    </AdaptationSet>
  </Period>
</MPD>"""


def b64url(data: bytes) -> str:
    return fastevo.b64url(data)


def fck3(keys: dict[str, str]) -> bytes:
    body = b"".join(bytes.fromhex(kid) + bytes.fromhex(key) for kid, key in keys.items())
    return b"FCK3" + bytes([3, 1]) + struct.pack(">H", len(keys)) + body


def tenc_head(kid: str) -> bytes:
    """An MP4 start whose tenc box names ``kid``."""
    tenc = b"tenc" + bytes(4) + bytes([0, 0x11, 1, 0]) + bytes.fromhex(kid)
    return b"\x00" * 100 + struct.pack(">I", len(tenc) + 4) + tenc + b"\x00" * 50


# A stand-in for the web player's key pair, served in a player script the
# way Fastevo's own carries it (a JS string with \\x escapes).
PLAYER_KEY = RSA.generate(2048)


def js_literal(pem: str) -> str:
    return pem.replace(" ", "\\x20").replace("\n", "\\x5cn")


PLAYER_PAGE_HTML = '<script type=importmap></script><script src=player.0123abcd.js type=module>'
PLAYER_SCRIPT = (
    "a1YG=JSON['parse']('{\\x22name\\x22:\\x22fortiflix-player\\x22,"
    "\\x22version\\x22:\\x221.0.999\\x22}');"
    f"let a0jm='{js_literal(PLAYER_KEY.public_key().export_key().decode())}'"
    "['replace'](/\\\\n/g,'\\x0a'),"
    f"a0ju='{js_literal(PLAYER_KEY.export_key(pkcs=8).decode())}'"
    "['replace'](/\\\\n/g,'\\x0a');"
)


class FakeFastevo:
    """Fastevo's side: identities, playback, links, manifest, tracks, license."""

    def __init__(self) -> None:
        self.client_public = PLAYER_KEY.public_key()
        self.client_version: str | None = None
        self.session_secret = bytes.fromhex("42" * 32)
        self.session_token = "playback-session-token"
        self.requests: list[tuple[str, str]] = []
        self.client_jwk: dict | None = None
        self.license_body: dict | None = None

    def seal(self, data: dict) -> dict:
        """An answer as Fastevo sends it: AES-CBC, key sealed to the client."""
        key, iv = bytes(range(32)), bytes(range(16))
        ct = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(json.dumps(data).encode(), 16))
        sealed = PKCS1_OAEP.new(self.client_public, hashAlgo=SHA256).encrypt(key)
        return {"e": b64url(ct), "k": b64url(sealed), "i": b64url(iv)}

    def clear_key_session(self, client_jwk: dict) -> dict:
        client = ECC.construct(
            curve="p256",
            point_x=int.from_bytes(fastevo.b64_decode(client_jwk["x"]), "big"),
            point_y=int.from_bytes(fastevo.b64_decode(client_jwk["y"]), "big"),
        ).pointQ
        server = ECC.generate(curve="p256")
        shared = int((client * server.d).x).to_bytes(32, "big")
        salt = bytes.fromhex("10" * 32)
        wrap = HKDF(shared, 32, salt, SHA256, context=b"fastevo-clearkey-v3/session-secret-wrap")
        thumbprint = b64url(SHA256.new(json.dumps(client_jwk, separators=(",", ":")).encode()).digest())
        iv = bytes.fromhex("01" * 12)
        cipher = AES.new(wrap, AES.MODE_GCM, nonce=iv)
        cipher.update(b"v3\n" + thumbprint.encode())
        ct, tag = cipher.encrypt_and_digest(self.session_secret)
        return {
            "version": 3,
            "licensePath": fastevo.LICENSE_PATH,
            "serverPublicJwk": {
                "crv": "P-256", "kty": "EC",
                "x": b64url(int(server.pointQ.x).to_bytes(32, "big")),
                "y": b64url(int(server.pointQ.y).to_bytes(32, "big")),
            },
            "salt": b64url(salt), "iv": b64url(iv),
            "ciphertext": b64url(ct), "authenticationTag": b64url(tag),
        }

    def license(self, body: dict) -> dict:
        token_hash = SHA256.new(self.session_token.encode()).digest()
        response_key = HKDF(
            self.session_secret, 32, token_hash, SHA256,
            context=b"fastevo-clearkey-v3/response-encryption",
        )
        canonical = "\n".join([
            "v3", "POST", fastevo.LICENSE_PATH, b64url(token_hash), str(body["timestamp"]),
            body["nonce"], body["type"], ",".join(body["kids"]),
        ])
        wanted = {fastevo.b64_decode(kid).hex() for kid in body["kids"]}
        iv = bytes.fromhex("09" * 12)
        cipher = AES.new(response_key, AES.MODE_GCM, nonce=iv)
        cipher.update(canonical.encode())
        ct, tag = cipher.encrypt_and_digest(fck3({k: v for k, v in KEYS.items() if k in wanted}))
        return {"version": 3, "iv": b64url(iv), "ciphertext": b64url(ct), "authenticationTag": b64url(tag)}


class FakeResponse:
    def __init__(self, status: int, payload=None, text: str = "", body: bytes = b"") -> None:
        self.status = status
        self._payload = payload
        self._text = text
        self.content = self
        self._body = body

    async def json(self, content_type=None):
        return self._payload

    async def text(self):
        return self._text

    async def read(self, n=-1):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeHTTP:
    def __init__(self, server: FakeFastevo) -> None:
        self.server = server

    def get(self, url, headers=None):
        self.server.requests.append(("GET", url))
        if url == fastevo.PLAYER_PAGE:
            return FakeResponse(200, text=PLAYER_PAGE_HTML)
        if url == "https://webplay.mp2.fastevo.net/release/player.0123abcd.js":
            return FakeResponse(200, text=PLAYER_SCRIPT)
        if url.endswith("/identities"):
            return FakeResponse(200, self.server.seal({"etagIdentityClaim": "etag"}))
        if "master.mpd" in url:
            return FakeResponse(200, text=MANIFEST)
        if "audio/fullTrack.m4a" in url:
            return FakeResponse(206, body=tenc_head(AUDIO_KID))
        if "video/1080p/fullTrack.mp4" in url:
            return FakeResponse(206, body=tenc_head(VIDEO_KID))
        return FakeResponse(404)

    def post(self, url, headers=None, json=None, data=None):
        self.server.requests.append(("POST", url))
        if url.endswith("/playback/initiate"):
            assert headers["authorization"] == "v4.local.play-token"
            # The request is sealed with the player's public key.
            sealed_key = PKCS1_OAEP.new(PLAYER_KEY, hashAlgo=SHA256).decrypt(
                fastevo.b64_decode(json["k"])
            )
            from Crypto.Util.Padding import unpad

            payload = __import__("json").loads(unpad(
                AES.new(sealed_key, AES.MODE_CBC, fastevo.b64_decode(json["i"])).decrypt(
                    fastevo.b64_decode(json["e"])
                ),
                16,
            ))
            self.server.client_version = payload["clientVersion"]
            # The client's key exchange half travels sealed to Fastevo; the
            # stand-in takes it from the session the test kept.
            jwk = self.server.client_jwk
            return FakeResponse(200, self.server.seal({
                "currentTimestamp": "2026-11-19T09:00:00Z",
                "playbackData": {
                    "playbackSessionExchangesToken": self.server.session_token,
                    "mediaPlaylistUrl": f"{HOST}/{VIDEO_ID}/processed/video/content/media/master.mpd",
                    "mediaPlaylistAccessTokenDetails": {"queryParams": {"token": "abc"}},
                    "clearKeySession": self.server.clear_key_session(jwk),
                },
            }))
        if "/identities/link" in url:
            return FakeResponse(200, {})
        if url.endswith(fastevo.LICENSE_PATH):
            body = __import__("json").loads(data)
            self.server.license_body = body
            return FakeResponse(200, self.server.license(body))
        return FakeResponse(404)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def make_drm(monkeypatch, server: FakeFastevo) -> fastevo.FastevoDRM:
    monkeypatch.setattr(fastevo.aiohttp, "ClientSession", lambda **_: FakeHTTP(server))
    real_session = fastevo.ClearKeySession

    def keep_session():
        session = real_session()
        server.client_jwk = session.public_jwk
        return session

    monkeypatch.setattr(fastevo, "ClearKeySession", keep_session)
    monkeypatch.setattr(fastevo, "_player_keys_cache", None)
    drm = fastevo.FastevoDRM.__new__(fastevo.FastevoDRM)
    drm.authed = None
    drm._crypto = None
    drm.client_version = fastevo.CLIENT_VERSION
    return drm


def drm_media(token="v4.local.play-token") -> DRMMedia:
    return DRMMedia(
        media_id=7,
        manifest_url=f"{HOST}/{VIDEO_ID}/processed/video/content/media/master.mpd",
        key_pair_id="",
        policy="",
        signature=token,
        content_id=1,
    )


@pytest.mark.asyncio
async def test_a_video_resolves_to_its_best_tracks_and_their_keys(monkeypatch):
    server = FakeFastevo()
    drm = make_drm(monkeypatch, server)
    media = drm_media()

    video_url, audio_url, key = await drm.resolve_drm(media)

    base = f"{HOST}/{VIDEO_ID}/processed/video/content/media"
    assert video_url == f"{base}/video/1080p/fullTrack.mp4?token=abc"
    assert audio_url == f"{base}/audio/fullTrack.m4a?token=abc"
    # Each track's own tenc key id, not the manifest's default_KID (...ff).
    assert key == f"{VIDEO_KID}:{KEYS[VIDEO_KID]} {AUDIO_KID}:{KEYS[AUDIO_KID]}"
    assert ("GET", audio_url) in server.requests and ("GET", video_url) in server.requests
    assert server.license_body is not None and len(server.license_body["kids"]) == 2
    # mp4decrypt gets one --key per track key.
    assert mp4decrypt_key_arguments(key) == [
        "--key", f"{VIDEO_KID}:{KEYS[VIDEO_KID]}", "--key", f"{AUDIO_KID}:{KEYS[AUDIO_KID]}",
    ]
    assert (media.video_url, media.audio_url) == (video_url, audio_url)
    # The keys and version come from the player script, fetched once.
    assert server.client_version == "1.0.999"
    await drm.resolve_drm(drm_media())
    assert [r for r in server.requests if "/release/" in r[1]] == [
        ("GET", fastevo.PLAYER_PAGE),
        ("GET", "https://webplay.mp2.fastevo.net/release/player.0123abcd.js"),
    ]


def test_the_repository_holds_no_fastevo_key():
    source = Path(fastevo.__file__).read_text()
    assert "PRIVATE KEY-----" not in source and "PUBLIC KEY-----" not in source


def test_a_player_script_without_keys_is_refused():
    with pytest.raises(fastevo.FastevoError):
        fastevo.parse_player_script("let a0jm='nothing here';")
    assert fastevo.player_script_url("<html></html>") is None


@pytest.mark.asyncio
async def test_media_without_a_play_token_is_refused(monkeypatch):
    drm = make_drm(monkeypatch, FakeFastevo())
    with pytest.raises(fastevo.FastevoError):
        await drm.resolve_drm(drm_media(token="cloudfront-signature"))


def test_a_fastevo_video_is_named_by_its_id_and_sends_no_cloudfront_cookie():
    media = drm_media()
    assert media.is_fastevo and media.get_cookies() == ""
    assert media.resolve_filename() == f"{VIDEO_ID}.mp4"
    media.video_url = f"{HOST}/{VIDEO_ID}/processed/video/content/media/video/1080p/fullTrack.mp4?t=1"
    assert media.resolve_filename() == f"{VIDEO_ID}.mp4"
    onlyfans = DRMMedia(7, "https://cdn3.onlyfans.com/dash/files/a/b/manifest.mpd", "K", "P", "S", 1)
    assert not onlyfans.is_fastevo and "CloudFront-Signature=S" in onlyfans.get_cookies()
    assert mp4decrypt_key_arguments("aa:bb") == ["--key", "aa:bb"]


def test_tracks_are_fetched_with_the_players_origin():
    headers = fastevo.media_request_headers(f"{HOST.replace('.test', '.net')}/x/fullTrack.mp4")
    assert headers["Origin"] == fastevo.WEBPLAY_BASE
    assert fastevo.media_request_headers("https://cdn.test/a.jpg") == {}


def test_a_license_envelope_must_be_well_formed():
    assert fastevo.unpack_fck3_envelope(fck3({VIDEO_KID: KEYS[VIDEO_KID]})) == [
        (VIDEO_KID, KEYS[VIDEO_KID])
    ]
    with pytest.raises(ValueError, match="magic"):
        fastevo.unpack_fck3_envelope(b"XXXX" + bytes(36))
    with pytest.raises(ValueError, match="length"):
        fastevo.unpack_fck3_envelope(b"FCK3" + bytes([3, 1]) + struct.pack(">H", 2) + bytes(32))


def test_the_darkfans_auth_offers_fastevo_drm(monkeypatch):
    from ultima_scraper_api.apis.darkfans.classes.auth_model import DarkFansAuthModel

    auth = DarkFansAuthModel.__new__(DarkFansAuthModel)
    monkeypatch.setattr(fastevo.FastevoDRM, "__init__", lambda self, authed: None)
    assert isinstance(auth.drm, fastevo.FastevoDRM)

    def missing(self, authed):
        raise FileNotFoundError("mp4decrypt not found")

    other = DarkFansAuthModel.__new__(DarkFansAuthModel)
    monkeypatch.setattr(fastevo.FastevoDRM, "__init__", missing)
    assert other.drm is None


class FakeRun:
    def __init__(self, returncode=0, stderr=b""):
        self.returncode, self.stderr = returncode, stderr


class FakeFormatter:
    """Records commands; mp4dump reports an encrypted video, shaka writes output."""

    def __init__(self, decode_errors=b"", shaka_code=0):
        self.commands: list[list[str]] = []
        self.decode_errors = decode_errors
        self.shaka_code = shaka_code

    async def run_process(self, args, *, stdout_consumer=None):
        self.commands.append(args)
        if args[0].endswith("mp4dump"):
            stdout_consumer(b"[stsd] ... [encv] size=8+100")
        elif args[0].endswith("shaka-packager"):
            if self.shaka_code:
                return FakeRun(self.shaka_code, f"bad key {KEYS[VIDEO_KID]}".encode())
            output = args[1].split("output=", 1)[1]
            Path(output).write_bytes(b"clear")
        elif args[0] == "ffmpeg":
            return FakeRun(0, self.decode_errors)
        return FakeRun()


def shaka_drm(formatter):
    drm = fastevo.FastevoDRM.__new__(fastevo.FastevoDRM)
    drm.media_formatter = formatter
    drm.mp4dump_filepath = Path("/usr/bin/mp4dump")
    drm.shaka_filepath = Path("/usr/bin/shaka-packager")
    return drm


KEY = f"{VIDEO_KID}:{KEYS[VIDEO_KID]} {AUDIO_KID}:{KEYS[AUDIO_KID]}"


@pytest.mark.asyncio
async def test_tracks_decrypt_with_shaka_and_must_decode(tmp_path):
    stream = tmp_path / "v_video.enc.mp4"
    stream.write_bytes(b"encrypted")
    formatter = FakeFormatter()

    output = await shaka_drm(formatter).decrypt_file_async(stream, KEY, temp_output_path=tmp_path)

    assert output == tmp_path / "v_video.dec.mp4" and output.read_bytes() == b"clear"
    assert not stream.exists()  # the encrypted copy goes once the clear one is kept
    shaka = next(c for c in formatter.commands if c[0].endswith("shaka-packager"))
    assert "stream=video" in shaka[1]
    assert shaka[-1] == (
        f"label=k0:key_id={VIDEO_KID}:key={KEYS[VIDEO_KID]},"
        f"label=k1:key_id={AUDIO_KID}:key={KEYS[AUDIO_KID]}"
    )
    assert any(c[0] == "ffmpeg" for c in formatter.commands)


@pytest.mark.asyncio
async def test_a_track_that_does_not_decode_is_not_kept(tmp_path):
    stream = tmp_path / "v_video.enc.mp4"
    stream.write_bytes(b"encrypted")

    with pytest.raises(RuntimeError, match="does not decode"):
        await shaka_drm(FakeFormatter(decode_errors=b"error while decoding MB 0 0")).decrypt_file_async(
            stream, KEY, temp_output_path=tmp_path
        )
    assert stream.exists() and not (tmp_path / "v_video.dec.mp4").exists()


@pytest.mark.asyncio
async def test_shaka_errors_do_not_show_keys(tmp_path):
    stream = tmp_path / "v_video.enc.mp4"
    stream.write_bytes(b"encrypted")

    with pytest.raises(RuntimeError) as failure:
        await shaka_drm(FakeFormatter(shaka_code=2)).decrypt_file_async(stream, KEY, temp_output_path=tmp_path)
    assert KEYS[VIDEO_KID] not in str(failure.value)
    assert fastevo.FastevoDRM.decrypts_own_streams
