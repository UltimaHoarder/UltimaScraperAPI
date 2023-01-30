from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Generator

from ultima_scraper_api.classes.prepare_directories import DirectoryManager

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.fansly import start as FanslyAPI
    from ultima_scraper_api.apis.onlyfans.onlyfans import start as OnlyFansAPI

    api_types = OnlyFansAPI | FanslyAPI


class FilesystemManager:
    def __init__(self) -> None:
        self.user_data_directory = Path("__user_data__")
        self.trash_directory = self.user_data_directory.joinpath("trash")
        self.profiles_directory = self.user_data_directory.joinpath("profiles")
        self.settings_directory = Path("__settings__")
        self.ignore_files = ["desktop.ini", ".DS_Store", ".DS_store", "@eaDir"]
        self.directory_manager: DirectoryManager | None = None

    def __iter__(self):
        for each in self.__dict__.values():
            yield each

    def check(self):
        for directory in self:
            if isinstance(directory, Path):
                directory.mkdir(exist_ok=True)

    def remove_mandatory_files(
        self, files: list[Path] | Generator[Path, None, None], keep: list[str] = []
    ):
        folders = [x for x in files if x.name not in self.ignore_files]
        if keep:
            folders = [x for x in files if x.name in keep]
        return folders

    def activate_directory_manager(self, api: api_types):
        from ultima_scraper_api.helpers import main_helper

        site_settings = api.get_site_settings()
        root_metadata_directory = main_helper.check_space(
            site_settings.metadata_directories
        )
        root_download_directory = main_helper.check_space(
            site_settings.download_directories
        )
        self.directory_manager = DirectoryManager(
            site_settings,
            root_metadata_directory,
            root_download_directory,
        )
