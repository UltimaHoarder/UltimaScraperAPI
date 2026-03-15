from pathlib import Path

from pydantic import BaseModel


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


class DownloadSettings(BaseModel):
    max_concurrency: int = 64
    per_domain_concurrency: int = 8
    head_concurrency: int = 64
    buffer_size_bytes: int = 10 * 1024 * 1024


class Proxy(BaseModel):
    url: str
    username: str | None = None
    password: str | None = None
    max_connections: int = -1
    downloads: DownloadSettings = DownloadSettings()


class Network(BaseModel):
    max_connections: int = -1
    proxies: list[Proxy] = []
    proxy_fallback: bool = False
    downloads: DownloadSettings = DownloadSettings()


class Server(BaseModel):
    host: str = "localhost"
    port: int = 8080
    active: bool = False


class Redis(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    enabled: bool = True


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
    redis: Redis = Redis()


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


class LoyalFansAPIConfig(GlobalAPI):
    class LoyalFansCache(GlobalCache):
        pass

    cache: LoyalFansCache = LoyalFansCache()


class Sites(BaseModel):
    onlyfans: OnlyFansAPIConfig = OnlyFansAPIConfig()
    fansly: FanslyAPIConfig = FanslyAPIConfig()
    loyalfans: LoyalFansAPIConfig = LoyalFansAPIConfig()

    def get_settings(self, site_name: str):
        if site_name == "OnlyFans":
            return self.onlyfans
        elif site_name == "Fansly":
            return self.fansly
        else:
            return self.loyalfans


class UltimaScraperAPIConfig(BaseModel):
    settings: Settings = Settings()
    site_apis: Sites = Sites()


api_config_types = OnlyFansAPIConfig | FanslyAPIConfig | LoyalFansAPIConfig
