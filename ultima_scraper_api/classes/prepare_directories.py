import copy
from pathlib import Path
from typing import Any

from ultima_scraper_api.classes.make_settings import SiteSettings
from ultima_scraper_api.classes.prepare_metadata import format_attributes


class FormatTypes:
    def __init__(self, site_settings: SiteSettings) -> None:
        self.metadata_directory_format = site_settings.metadata_directory_format
        self.file_directory_format = site_settings.file_directory_format
        self.filename_format = site_settings.filename_format

    def check_rules(self):
        """Checks for invalid filepath

        Returns:
            tuple(str,bool): Returns a string which explains invalid filepath format
        """
        bool_status = True
        wl = []
        invalid_list = []
        string = ""
        for key, _value in self:
            if key == "file_directory_format":
                bl = format_attributes()
                wl = [v for _k, v in bl.__dict__.items()]
                bl = bl.whitelist(wl)
                invalid_list = []
                for b in bl:
                    if b in self.file_directory_format.as_posix():
                        invalid_list.append(b)
            if key == "filename_format":
                bl = format_attributes()
                wl = [v for _k, v in bl.__dict__.items()]
                bl = bl.whitelist(wl)
                invalid_list = []
                for b in bl:
                    if b in self.filename_format.as_posix():
                        invalid_list.append(b)
            if key == "metadata_directory_format":
                wl = [
                    "{site_name}",
                    "{first_letter}",
                    "{model_id}",
                    "{profile_username}",
                    "{model_username}",
                ]
                bl = format_attributes().whitelist(wl)
                invalid_list: list[str] = []
                for b in bl:
                    if b in self.metadata_directory_format.as_posix():
                        invalid_list.append(b)
            if invalid_list:
                string += f"You cannot use {','.join(invalid_list)} in {key}. Use any from this list {','.join(wl)}"
                bool_status = False

        return string, bool_status

    def check_unique(self):
        values: list[str] = []
        unique = []
        new_format_copied = copy.deepcopy(self)
        option: dict[str, Any] = {}
        option["string"] = ""
        option["bool_status"] = True
        option["unique"] = new_format_copied
        f = format_attributes()
        for key, value in self:
            value: Path
            if key == "file_directory_format":
                unique = ["{media_id}", "{model_username}"]
                values = list(value.parts)
                option["unique"].file_directory_format = unique
            elif key == "filename_format":
                values = []
                unique = ["{media_id}", "{filename}"]
                for _key2, value2 in f:
                    if value2 in value.as_posix():
                        values.append(value2)
                option["unique"].filename_format = unique
            elif key == "metadata_directory_format":
                unique = ["{model_username}"]
                values = list(value.parts)
                option["unique"].metadata_directory_format = unique
            if key != "filename_format":
                e = [x for x in values if x in unique]
            else:
                e = [x for x in unique if x in values]
            if e:
                setattr(option["unique"], key, e)
            else:
                option[
                    "string"
                ] += f"{key} is a invalid format since it has no unique identifiers. Use any from this list {','.join(unique)}\n"
                option["bool_status"] = False
        return option

    def __iter__(self):
        for attr, value in self.__dict__.items():
            yield attr, value
