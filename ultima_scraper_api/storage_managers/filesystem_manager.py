from pathlib import Path


class FilesystemManager:
    def __init__(self) -> None:
        self.user_data_directory = Path("__user_data__")
        self.trash_directory = self.user_data_directory.joinpath("trash")
        self.profiles_directory = self.user_data_directory.joinpath("profiles")
        self.settings_directory = Path("__settings__")

    def __iter__(self):
        for each in self.__dict__.values():
            yield each

    def check(self):
        directory: Path
        for directory in self:
            directory.mkdir(exist_ok=True)
            pass
