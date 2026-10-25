import json
import os
import tempfile
from pathlib import Path
from typing import Self

from platformdirs import user_config_dir
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


class Proxy(BaseModel):
    url: str
    username: str | None = None
    password: str | None = None
    enabled: bool = True
    max_connections: int = -1
    group: str | None = None
    guest_lookup_timeout: float | None = None


class Network(BaseModel):
    max_connections: int = -1
    proxies: list[Proxy] = []
    proxy_fallback: bool = False
    # Guest requests per second per route (proxy IP) across all workers.
    # OnlyFans answers more than ~38/s from one IP with HTTP 429. 0 disables.
    guest_route_rate_limit: float = Field(default=35.0, ge=0)
    # Give each proxy a fixed set of guest sessions (visitors) shared across
    # workers. OnlyFans also limits each guest session to about 3 requests/s,
    # so spreading a proxy's traffic over many sessions avoids HTTP 429.
    guest_session_pool: bool = True
    # Maximum duration in seconds to wait for guest user lookup across proxy routes before timing out.
    guest_lookup_timeout: float = Field(default=3.5, ge=0.5)
    # Maximum duration in seconds for guest route HTTP requests before timing out.
    guest_route_timeout: float = Field(default=3.0, ge=0.5)


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


class Settings(BaseModel):
    network: Network = Network()
    drm: DRM = DRM()
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

    @classmethod
    def get_config_path(cls) -> Path:
        config_dir = user_config_dir("ultima_scraper_api")
        return Path(config_dir) / "config.json"

    @classmethod
    def load_config(cls, path: Path | None = None) -> Self:
        config_path = path or cls.get_config_path()
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        return cls.model_validate(payload)

    @classmethod
    def load_or_create_default_config(cls, path: Path | None = None) -> Self:
        config_path = path or cls.get_config_path()
        if config_path.is_file():
            return cls.load_config(config_path)
        config = cls()
        config.save_config(config_path)
        return config

    def save_config(self, path: Path | None = None) -> Path:
        config_path = path or self.get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.model_dump(mode="json")
        serialized = json.dumps(payload, indent=2)
        file_descriptor, temporary_path_raw = tempfile.mkstemp(
            dir=config_path.parent,
            prefix=f".{config_path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_path_raw)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as config_file:
                config_file.write(serialized)
                config_file.flush()
                os.fsync(config_file.fileno())
            os.replace(temporary_path, config_path)
        finally:
            temporary_path.unlink(missing_ok=True)
        return config_path


api_config_types = OnlyFansAPIConfig | FanslyAPIConfig | LoyalFansAPIConfig

