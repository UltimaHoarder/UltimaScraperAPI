from pathlib import Path
from typing import Literal

from pydantic import BaseModel

site_name_literals = Literal["OnlyFans", "Fansly"]


class Webhook(BaseModel):
    url: str | None = None
    hide_info: list[str] = []
    active: bool


class Webhooks(BaseModel):
    auth: Webhook = Webhook(active=False)
    download: Webhook = Webhook(active=False)


class MediaQuality(BaseModel):
    image: str = "source"
    video: str = "source"
    audio: str = "source"


class Network(BaseModel):
    max_threads: int = -1
    proxies: list[str] = []
    proxy_fallback: bool = True


class Server(BaseModel):
    host: str = "localhost"
    port: int = 8080
    active: bool = False


class GlobalCache(BaseModel):
    pass


class DRM(BaseModel):
    device_client_blob_filepath: Path | None = None
    device_private_key_filepath: Path | None = None
    decrypt_media_path: Path | None = None


class Settings(BaseModel):
    private_key_filepath: Path | None = None
    network: Network = Network()
    drm: DRM = DRM()
    server: Server = Server()


class GlobalAPI(BaseModel):
    media_quality: MediaQuality = MediaQuality()
    webhooks: Webhooks = Webhooks()


class OnlyFansAPIConfig(GlobalAPI):
    class OnlyFansCache(GlobalCache):
        paid_content: int = 3600 * 1

    dynamic_rules_url: str = (
        "https://raw.githubusercontent.com/DATAHOARDERS/dynamic-rules/main/onlyfans.json"
    )
    cache: OnlyFansCache = OnlyFansCache()


class FanslyAPIConfig(GlobalAPI):
    class FanslyCache(GlobalCache):
        pass

    cache: FanslyCache = FanslyCache()


class Sites(BaseModel):
    onlyfans: OnlyFansAPIConfig = OnlyFansAPIConfig()
    fansly: FanslyAPIConfig = FanslyAPIConfig()

    def get_settings(self, site_name: site_name_literals):
        if site_name == "OnlyFans":
            return self.onlyfans
        else:
            return self.fansly


class UltimaScraperAPIConfig(BaseModel):
    settings: Settings = Settings()
    site_apis: Sites = Sites()


api_config_types = OnlyFansAPIConfig | FanslyAPIConfig
