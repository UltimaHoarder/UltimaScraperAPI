from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


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
    max_concurrency: int = Field(default=64, gt=0, strict=True)
    # When omitted, file admission follows the configured part-request budget.
    max_file_concurrency: int | None = Field(default=None, gt=0, strict=True)
    per_domain_concurrency: int = Field(default=8, gt=0, strict=True)
    head_concurrency: int = Field(default=64, gt=0, strict=True)
    buffer_size_bytes: int = Field(default=10 * 1024 * 1024, gt=0, strict=True)


class PluginProxyOwner(BaseModel):
    plugin_id: str
    source: str
    provider_id: str


class Proxy(BaseModel):
    url: str
    username: str | None = None
    password: str | None = None
    enabled: bool = True
    max_connections: int = -1
    downloads: DownloadSettings = DownloadSettings()
    group: str | None = None
    managed_by: PluginProxyOwner | None = None


class Network(BaseModel):
    max_connections: int = -1
    proxies: list[Proxy] = []
    proxy_fallback: bool = False
    # Host-owned receipts commit with the proxy snapshot; never contain credentials.
    plugin_sync_receipts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # Guest requests per second per route (proxy IP) across all workers.
    # OnlyFans answers more than ~38/s from one IP with HTTP 429. 0 disables.
    guest_route_rate_limit: float = Field(default=35.0, ge=0)
    # Give each proxy a fixed set of guest sessions (visitors) shared across
    # workers. OnlyFans also limits each guest session to about 3 requests/s,
    # so spreading a proxy's traffic over many sessions avoids HTTP 429.
    guest_session_pool: bool = True
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
