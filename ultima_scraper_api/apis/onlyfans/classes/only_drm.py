import platform
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import orjson
import xmltodict
from pywidevine.cdm import Cdm
from pywidevine.device import Device, DeviceTypes
from pywidevine.pssh import PSSH
from ultima_scraper_api.apis.onlyfans.classes.extras import endpoint_links

if TYPE_CHECKING:
    import ultima_scraper_api

    auth_types = ultima_scraper_api.auth_types
os_name = platform.system()
# Replace authed with your ClientSession
# Replace endpoint_links.drm_resolver with "https://onlyfans.com/api2/v2/users/media/{MEDIA_ID}/drm/{RESPONSE_TYPE}/{CONTENT_ID}?type=widevine"
# If the content is from mass messages, omit the response_type and content_id, the end result will look like "https://onlyfans.com/api2/v2/users/media/{MEDIA_ID}/drm/?type=widevine"
# media_item is a Post's media from the "https://onlyfans.com/api2/v2/posts/{USER_ID}?skip_users=all" api


class OnlyDRM:
    def __init__(
        self, client_key_path: Path, private_key_path: Path, authed: "auth_types"
    ) -> None:
        self.client_key = client_key_path.read_bytes()
        self.private_key = private_key_path.read_bytes()
        self.device = Device(
            type_=DeviceTypes.ANDROID,
            security_level=3,
            flags={},
            client_id=self.client_key,
            private_key=self.private_key,
        )
        self.cdm = Cdm.from_device(self.device)
        self.session_id = self.cdm.open()
        self.authed = authed

    def has_drm(self, media_item: dict[str, Any]):
        try:
            return self.get_dash_url(media_item)
        except KeyError as _e:
            pass

    def extract_hex_id(self, dash_url: str):
        match = re.search(r"/([0-9a-f]{32})/", dash_url)
        assert match
        hex_id = match.group(1)
        return hex_id

    def extract_directory_from_url(self, dash_url: str):
        match = re.search(r"files/(.*?)/\w+\.mpd$", dash_url)
        assert match
        directory = match.group(1)
        return directory

    def get_dash_url(self, media_item: dict[str, Any]):
        drm = media_item["files"]["drm"]
        manifest = drm["manifest"]
        dash: str = manifest["dash"]
        return dash

    async def get_signature(self, media_item: dict[str, Any]):
        drm = media_item["files"]["drm"]
        signature = drm["signature"]["dash"]
        cookie_str = ""
        for key, value in signature.items():
            cookie_str += f"{key}={value}; "
        signature_str = cookie_str.strip()
        return signature_str

    async def get_mpd(self, media_item: dict[str, Any]):
        drm = media_item["files"]["drm"]
        manifest = drm["manifest"]
        signature = drm["signature"]["dash"]
        cookie_str = ""
        for key, value in signature.items():
            cookie_str += f"{key}={value}; "
        cookie_str = cookie_str.strip()
        dash = manifest["dash"]
        r = await self.authed.get_requester().request(
            dash, premade_settings="", custom_cookies=cookie_str
        )
        xml = xmltodict.parse(await r.text())
        mpd: dict[str, Any] = orjson.loads(orjson.dumps(xml))
        return mpd

    async def get_pssh(self, mpd: dict[str, Any]):
        tracks = mpd["MPD"]["Period"]["AdaptationSet"]
        pssh_str = ""
        for video_tracks in tracks:
            if video_tracks["@mimeType"] == "video/mp4":
                for t in video_tracks["ContentProtection"]:
                    if (
                        t["@schemeIdUri"].lower()
                        == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"
                    ):
                        pssh_str = t["cenc:pssh"]
                        return pssh_str

    async def get_license(
        self, content_item: dict[str, Any], media_item: dict[str, Any], raw_pssh: str
    ):
        pssh = PSSH(raw_pssh)
        challenge = self.cdm.get_license_challenge(self.session_id, pssh)
        url = endpoint_links().drm_resolver(
            media_item["id"], content_item.get("responseType"), content_item.get("id")
        )
        licence = await self.authed.get_requester().request(
            url, method="POST", data=challenge
        )
        return await licence.read()

    async def get_keys(self, licence: bytes):
        session_id = self.session_id
        cdm = self.cdm
        cdm.parse_license(session_id, licence)
        keys = cdm.get_keys(session_id)
        return keys

    def get_video_url(self, mpd: dict[str, Any], media_item: dict[str, Any]):
        dash_url = self.get_dash_url(media_item)
        directory_url = self.extract_directory_from_url(dash_url)
        adaptation_set = mpd["MPD"]["Period"]["AdaptationSet"][0]
        representation: list[dict[str, Any]] | dict[str, Any] = adaptation_set[
            "Representation"
        ]
        if isinstance(representation, list):
            base_url = representation[0]["BaseURL"]
        else:
            base_url = representation["BaseURL"]
        media_url = f"https://cdn3.onlyfans.com/dash/files/{directory_url}/{base_url}"
        return media_url

    def get_audio_url(self, mpd: dict[str, Any], media_item: dict[str, Any]):
        dash_url = self.get_dash_url(media_item)
        directory_url = self.extract_directory_from_url(dash_url)
        adaptation_set = mpd["MPD"]["Period"]["AdaptationSet"][1]
        representation: list[dict[str, Any]] | dict[str, Any] = adaptation_set[
            "Representation"
        ]
        if isinstance(representation, list):
            base_url: str = representation[0]["BaseURL"]
        else:
            base_url: str = representation["BaseURL"]
        media_url = f"https://cdn3.onlyfans.com/dash/files/{directory_url}/{base_url}"
        return media_url

    def decrypt_file(
        self, filepath: Path, key: str, temp_output_path: Path | None = None
    ):
        output_filepath = Path(filepath.as_posix().replace(".enc", ".dec"))
        if temp_output_path:
            output_filepath = temp_output_path.joinpath(output_filepath.name)
        if output_filepath.exists():
            return output_filepath
        temp_output_filepath = Path(f"{output_filepath.as_posix()}.part")
        mp4decrypt_path = "./drm_device/mp4decrypt"
        if os_name == "Windows":
            mp4decrypt_path = ".\\drm_device\\mp4decrypt"
        pid = subprocess.Popen(
            [
                mp4decrypt_path,
                f"{filepath.as_posix()}",
                temp_output_filepath,
                "--key",
                key,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        pid.wait()
        if pid.stderr:
            error = pid.stderr.read()
            if not error:
                filepath.unlink()
                temp_output_filepath.rename(output_filepath)
                return output_filepath
            else:
                raise Exception(error)
