from __future__ import annotations

import copy
import uuid as uuid
from pathlib import Path
from typing import Any, Literal, Tuple, get_args

import orjson
from yarl import URL

site_name_literals = Literal["OnlyFans", "Fansly"]
site_names: Tuple[site_name_literals, ...] = get_args(site_name_literals)

current_version = None


def fix(config: dict[str, Any] = {}) -> dict[str, Any]:
    global current_version
    if config:
        info = config.get("info", {})
        if not info:
            print(
                "If you're not using >= v7 release, please download said release so the script can properly update your config. \nIf you're using >= v7 release or you don't care about your current config settings, press enter to continue. If script crashes, delete config."
            )
            input()
        current_version = info["version"]

        settings = config.get("settings")
        if settings:
            settings.pop("profile_directories", None)
    return config


class SiteSettings:
    def __init__(self, option: dict[str, Any] = {}):
        option = self.update_site_settings(option)

        class jobs:
            def __init__(self, option: dict[str, Any] = {}) -> None:
                self.scrape = scrape(option.get("scrape", {}))
                self.metadata = metadata(option.get("metadata", {}))

        class scrape:
            def __init__(self, option: dict[str, bool] = {}) -> None:
                self.subscriptions = option.get("subscriptions", True)
                self.messages = option.get("messages", True)
                self.paid_contents = option.get("paid_contents", True)

        class browser:
            def __init__(self, option: dict[str, bool] = {}) -> None:
                self.auth = option.get("auth", True)

        class metadata:
            def __init__(self, option: dict[str, bool] = {}) -> None:
                self.posts = option.get("posts", True)
                self.comments = option.get("comments", True)

        self.auto_profile_choice: list[int | str] | int | str | bool = option.get(
            "auto_profile_choice", []
        )
        self.auto_model_choice: list[int | str] | int | str | bool = option.get(
            "auto_model_choice", False
        )
        self.auto_api_choice: list[int | str] | int | str | bool = option.get(
            "auto_api_choice", True
        )
        self.auto_media_choice: list[int | str] | int | str | bool = option.get(
            "auto_media_choice", ""
        )
        self.browser = browser(option.get("browser", {}))
        self.jobs = jobs(option.get("jobs", {}))
        self.download_directories = [
            Path(directory)
            for directory in option.get("download_directories", ["__user_data__/sites"])
        ]
        self.file_directory_format = Path(
            option.get(
                "file_directory_format",
                "{site_name}/{model_username}/{api_type}/{value}/{media_type}",
            )
        )
        self.filename_format = Path(option.get("filename_format", "{filename}.{ext}"))
        self.metadata_directories = [
            Path(directory)
            for directory in option.get("metadata_directories", ["__user_data__/sites"])
        ]
        self.metadata_directory_format = Path(
            option.get(
                "metadata_directory_format",
                "{site_name}/{model_username}/Metadata",
            )
        )
        self.delete_legacy_metadata = option.get("delete_legacy_metadata", False)
        self.text_length = option.get("text_length", 255)
        self.video_quality = option.get("video_quality", "source")
        self.overwrite_files = option.get("overwrite_files", False)
        self.date_format = option.get("date_format", "%d-%m-%Y")
        self.ignored_keywords = option.get("ignored_keywords", [])
        self.ignore_type = option.get("ignore_type", "")
        self.blacklists = option.get("blacklists", [])
        self.webhook = option.get("webhook", True)

    def update_site_settings(self, options: dict[str, Any]):
        new_options = copy.copy(options)
        for key, value in options.items():
            match key:
                case "auto_scrape_names":
                    new_options["auto_model_choice"] = value
                case "auto_scrape_apis":
                    new_options["auto_api_choice"] = value
                case "file_directory_format":
                    new_options["file_directory_format"] = value.replace(
                        "{username}", "{model_username}"
                    )
                case "filename_format":
                    new_options["filename_format"] = value.replace(
                        "{username}", "{model_username}"
                    )
                case "metadata_directory_format":
                    new_options["metadata_directory_format"] = value.replace(
                        "{username}", "{model_username}"
                    )
                case "blacklist_name":
                    new_options["blacklists"] = [value]
                case "jobs":
                    if not value.get("scrape"):
                        new_value: dict[str, Any] = {}
                        new_value["scrape"] = {}
                        new_value["scrape"]["subscriptions"] = value.get(
                            "scrape_names", True
                        )
                        new_value["scrape"]["paid_contents"] = value.get(
                            "scrape_paid_content", True
                        )
                        new_options["jobs"] = new_value
                    else:
                        new_options_2 = copy.copy(options[key]["scrape"])
                        for scrape_key, scrape_value in options[key]["scrape"].items():
                            match scrape_key:
                                case "paid_content":
                                    new_options_2["paid_contents"] = scrape_value
                                case _:
                                    pass
                        new_options[key]["scrape"] = new_options_2
                case _:
                    pass
        return new_options

    def get_available_jobs(self, value: str):
        job_category = getattr(self.jobs, value.lower())
        valid = {x[0]: x[1] for x in job_category.__dict__.items() if x[1]}
        return valid

    def check_if_user_in_auto(self, value: str):
        auto_model_choice = self.auto_model_choice
        if isinstance(auto_model_choice, (list, tuple)):
            if any(map(lambda x: x == value, auto_model_choice)):
                return True
        elif auto_model_choice == value or auto_model_choice is True:
            return True
        else:
            return False


class Settings(object):
    def __init__(
        self,
        auto_site_choice: str = "",
        export_type: str = "json",
        max_threads: int = -1,
        min_drive_space: int = 0,
        helpers: dict[str, bool] = {},
        webhooks: dict[str, Any] = {},
        exit_on_completion: bool = False,
        infinite_loop: bool = True,
        loop_timeout: int = 0,
        dynamic_rules_link: str = "https://raw.githubusercontent.com/DIGITALCRIMINALS/dynamic-rules/main/onlyfans.json",
        proxies: list[str] = [],
        cert: str = "",
        random_string: str = "",
        tui: dict[str, bool] = {},
    ):
        class webhooks_settings:
            def __init__(self, option: dict[str, Any] = {}) -> None:
                class webhook_template:
                    def __init__(self, option: dict[str, Any] = {}) -> None:
                        self.webhooks = option.get("webhooks", [])
                        self.status = option.get("status", None)
                        self.hide_sensitive_info = option.get(
                            "hide_sensitive_info", True
                        )

                class auth_webhook:
                    def __init__(self, option: dict[str, Any] = {}) -> None:
                        self.succeeded = webhook_template(option.get("succeeded", {}))
                        self.failed = webhook_template(option.get("failed", {}))

                    def get_webhook(self, name: Literal["succeeded", "failed"]):
                        if name == "succeeded":
                            return self.succeeded
                        else:
                            return self.failed

                class download_webhook:
                    def __init__(self, option: dict[str, Any] = {}) -> None:
                        self.succeeded = webhook_template(option.get("succeeded", {}))
                        self.failed = webhook_template(option.get("failed", {}))

                    def get_webhook(self, name: Literal["succeeded", "failed"]):
                        if name == "succeeded":
                            return self.succeeded
                        else:
                            return self.failed

                self.global_webhooks = option.get("global_webhooks", [])
                self.global_status = option.get("global_status", True)
                self.auth_webhook = auth_webhook(option.get("auth_webhook", {}))
                self.download_webhook = download_webhook(
                    option.get("download_webhook", {})
                )

        class helpers_settings:
            def __init__(self, option: dict[str, bool] = {}) -> None:
                self.renamer = option.get("renamer", True)
                self.reformat_media = option.get("reformat_media", True)
                self.downloader = option.get("downloader", True)
                self.delete_empty_directories = option.get(
                    "delete_empty_directories", False
                )

        class tui_settings:
            def __init__(self, option: dict[str, bool] = {}) -> None:
                self.active = option.get("active", False)
                self.host = option.get("host", "localhost")
                self.port = option.get("port", 2112)
                self.api_key = option.get("api_key", uuid.uuid1().hex)

        self.auto_site_choice = auto_site_choice
        self.export_type = export_type
        self.max_threads = max_threads
        self.min_drive_space = min_drive_space
        self.helpers = helpers_settings(helpers)
        self.webhooks = webhooks_settings(webhooks)
        self.exit_on_completion = exit_on_completion
        self.infinite_loop = infinite_loop
        self.loop_timeout = loop_timeout
        dynamic_rules_link_ = URL(dynamic_rules_link)
        self.dynamic_rules_link = str(dynamic_rules_link_)
        self.proxies = proxies
        self.cert = cert
        self.random_string = random_string if random_string else uuid.uuid1().hex
        self.tui = tui_settings(tui)


class Config(object):
    def __init__(
        self,
        info: dict[str, Any] = {},
        settings: dict[str, Any] = {},
        supported: dict[str, Any] = {},
    ):
        class Info(object):
            def __init__(self) -> None:
                self.version = 8.0

        class Supported(object):
            def __init__(
                self,
                onlyfans: dict[str, Any] = {},
                fansly: dict[str, Any] = {},
                patreon: dict[str, Any] = {},
                starsavn: dict[str, Any] = {},
            ):
                self.onlyfans = self.OnlyFans(onlyfans)
                self.fansly = self.Fansly(fansly)

            class OnlyFans:
                def __init__(self, module: dict[str, Any]):
                    self.settings = SiteSettings(module.get("settings", {}))

            class Fansly:
                def __init__(self, module: dict[str, Any]):
                    self.settings = SiteSettings(module.get("settings", {}))

            def get_settings(self, site_name: site_name_literals):
                if site_name == "OnlyFans":
                    return self.onlyfans.settings
                else:
                    return self.fansly.settings

        self.info = Info()
        self.settings = Settings(**settings)
        self.supported = Supported(**supported)
    def import_json(self, file_path:Path):
        with file_path.open(encoding="utf-8") as o_file:
            json_file = orjson.loads(o_file.read())
            return Config(**json_file)

    def export(self) -> Config:
        base = copy.deepcopy(self)
        for name in site_names:
            SS = base.supported.get_settings(site_name=name)
            for key, value in SS.__dict__.items():
                match key:
                    case "download_directories" | "metadata_directories":
                        items: list[Path] = value
                        new_list = [x.as_posix() for x in items]
                        SS.__dict__[key] = new_list
                    case "file_directory_format" | "filename_format" | "metadata_directory_format":
                        value_: Path = value
                        final_path = value_.as_posix()
                        SS.__dict__[key] = final_path
                    case _:
                        pass
        return base