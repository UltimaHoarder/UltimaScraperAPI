from pathlib import Path

from pydantic import BaseModel


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


class Settings(BaseModel):
    private_key_filepath: Path | None = None
    network: Network = Network()
    drm: DRM = DRM()
    server: Server = Server()


class GlobalAPI(BaseModel):
    pass


class OnlyFansAPI(GlobalAPI):
    class OnlyFansCache(GlobalCache):
        paid_content = 3600 * 1

    dynamic_rules_url: str = "https://raw.githubusercontent.com/DIGITALCRIMINALS/dynamic-rules/main/onlyfans.json"
    cache = OnlyFansCache()


class FanslyAPI(GlobalAPI):
    class FanslyCache(GlobalCache):
        pass

    cache = FanslyCache()


class Sites(BaseModel):
    onlyfans: OnlyFansAPI = OnlyFansAPI()
    fansly: FanslyAPI = FanslyAPI()


class UltimaScraperAPIConfig(BaseModel):
    settings: Settings = Settings()
    site_apis: Sites = Sites()
