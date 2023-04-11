from __future__ import annotations

import copy
import os
import shutil
from datetime import datetime
from itertools import chain, groupby
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import ultima_scraper_api
from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.onlyfans.classes.extras import media_types
from ultima_scraper_api.helpers import main_helper

if TYPE_CHECKING:
    from ultima_scraper_api.classes.prepare_directories import DirectoryManager

auth_types = ultima_scraper_api.auth_types
user_types = ultima_scraper_api.user_types
global_version = 2

# Supports legacy metadata (.json and .db format) and converts it into the latest format (.db)
class create_metadata(object):
    def __init__(
        self,
        metadata: list[dict[str, Any]] | dict[str, Any] = {},
        standard_format: bool = False,
        api_type: str = "",
    ) -> None:
        self.version = global_version
        fixed_metadata = self.fix_metadata(metadata, standard_format, api_type)
        self.content = format_content(
            fixed_metadata["version"], fixed_metadata["content"]
        ).content
        pass

    def fix_metadata(
        self,
        metadata: dict[str, Any] | list[dict[str, Any]],
        standard_format: bool = False,
        api_type: str = "",
    ):
        new_format: dict[str, Any] = {}
        new_format["version"] = 1
        new_format["content"] = {}
        if isinstance(metadata, list):
            version = 0.3
            for m in metadata:
                new_format["content"] |= self.fix_metadata(m)["content"]
                print
            metadata = new_format
        else:
            version = metadata.get("version", None)
        if any(x for x in metadata if x in media_types().__dict__.keys()):
            standard_format = True
            print
        if not version and not standard_format and metadata:
            legacy_metadata = metadata
            media_type = legacy_metadata.get("type", None)
            if not media_type:
                version = 0.1
                media_type = api_type if api_type else media_type
            else:
                version = 0.2
            if version == 0.2:
                legacy_metadata.pop("type")
            new_format["content"][media_type] = {}
            for key, posts in legacy_metadata.items():
                if all(isinstance(x, list) for x in posts):
                    posts = list(chain(*posts))
                new_format["content"][media_type][key] = posts
                print
            print
        elif standard_format:
            if any(x for x in metadata if x in media_types().__dict__.keys()):
                metadata.pop("directories", None)
                for key, status in metadata.items():
                    if isinstance(status, int):
                        continue
                    for key2, posts in status.items():
                        if all(x and isinstance(x, list) for x in posts):
                            posts = list(chain(*posts))
                            metadata[key][key2] = posts
                        print
                    print
                print
            new_format["content"] = metadata
            print
        else:
            if global_version == version:
                new_format = metadata
            else:
                print
        print
        if "content" not in new_format:
            print
        return new_format

    def compare_metadata(self, old_metadata: create_metadata) -> create_metadata:
        for key, value in old_metadata.content:
            new_value = getattr(self.content, key, None)
            if not new_value:
                continue
            if not value:
                setattr(old_metadata, key, new_value)
            for key2, value2 in value:
                new_value2 = getattr(new_value, key2)
                seen = set()
                old_status = []
                for d in value2:
                    if d.post_id not in seen:
                        seen.add(d.post_id)
                        old_status.append(d)
                    else:
                        print
                setattr(value, key2, old_status)
                value2 = old_status
                new_status = new_value2
                for post in old_status:
                    if key != "Texts":
                        for old_media in post.medias:
                            new_found = None
                            new_items = [
                                x for x in new_status if post.post_id == x.post_id
                            ]
                            if new_items:
                                for new_item in (x for x in new_items if not new_found):
                                    for new_media in (
                                        x for x in new_item.medias if not new_found
                                    ):
                                        new_found = test(new_media, old_media)
                                        print
                            if new_found:
                                for key3, v in new_found:
                                    if key3 in [
                                        "directory",
                                        "downloaded",
                                        "size",
                                        "filename",
                                    ]:
                                        continue
                                    setattr(old_media, key3, v)
                                setattr(new_found, "found", True)
                    else:
                        new_items = [x for x in new_status if post.post_id == x.post_id]
                        if new_items:
                            new_found = new_items[0]
                            for key3, v in new_found:
                                if key3 in [
                                    "directory",
                                    "downloaded",
                                    "size",
                                    "filename",
                                ]:
                                    continue
                                setattr(post, key3, v)
                            setattr(new_found, "found", True)
                        print
                for new_post in new_status:
                    not_found = []
                    if key != "Texts":
                        not_found = [
                            new_post
                            for media in new_post.medias
                            if not getattr(media, "found", None)
                        ][:1]
                    else:
                        found = getattr(new_post, "found", None)
                        if not found:
                            not_found.append(new_post)

                    if not_found:
                        old_status += not_found
                old_status.sort(key=lambda x: x.post_id, reverse=True)
        new_metadata = old_metadata
        return new_metadata

    def convert(
        self, convert_type: str = "json", keep_empty_items: bool = False
    ) -> dict[str, Any]:
        if not keep_empty_items:
            self.remove_empty()
        value: dict[str, Any] = {}
        if convert_type == "json":
            value = main_helper.object_to_json(self)
        return value

    def remove_empty(self):
        copied = copy.deepcopy(self)
        for k, v in copied:
            if not v:
                delattr(self, k)
            print
        return self

    def __iter__(self):
        for attr, value in self.__dict__.items():
            yield attr, value


class format_content(object):
    def __init__(
        self,
        version=None,
        temp_old_content: dict = {},
        export=False,
        reformat=False,
        args={},
    ):
        class assign_state(object):
            def __init__(self) -> None:
                self.valid = []
                self.invalid = []

            def __iter__(self):
                for attr, value in self.__dict__.items():
                    yield attr, value

        old_content = temp_old_content.copy()
        old_content.pop("directories", None)
        new_content = media_types(assign_states=assign_state)
        for key, new_item in new_content:
            old_item = old_content.get(key)
            if not old_item:
                continue
            for old_key, old_item2 in old_item.items():
                new_posts = []
                if global_version == version:
                    posts = old_item2
                    for old_post in posts:
                        post = self.post_item(old_post)
                        new_medias = []
                        for media in post.medias:
                            media["media_type"] = key
                            media2 = self.media_item(media)
                            new_medias.append(media2)
                        post.medias = new_medias
                        new_posts.append(post)
                        print

                elif version == 1:
                    old_item2.sort(key=lambda x: x["post_id"])
                    media_list = [
                        list(g)
                        for k, g in groupby(old_item2, key=lambda x: x["post_id"])
                    ]
                    for media_list2 in media_list:
                        old_post = media_list2[0]
                        post = self.post_item(old_post)
                        for item in media_list2:
                            item["media_type"] = key
                            media = self.media_item(item)
                            post.medias.append(media)
                        new_posts.append(post)
                else:
                    media_list = []
                    input("METADATA VERSION: INVALID")
                setattr(new_item, old_key, new_posts)
        self.content = new_content

    class post_item(create_metadata, object):
        def __init__(self, option={}):
            # create_metadata.__init__(self, option)
            self.post_id: int = option.get("post_id", None)
            self.text: str = option.get("text", "")
            self.price: float = option.get("price", 0)
            self.paid = option.get("paid", False)
            self.medias = option.get("medias", [])
            self.createdAt: str = option.get("createdAt", option.get("postedAt", ""))

    class media_item(create_metadata):
        def __init__(self, option={}):
            # create_metadata.__init__(self, option)
            self.media_id = option.get("media_id", None)
            link = option.get("link", [])
            if link:
                link = [link]
            self.links = option.get("links", link)
            self.directory = option.get("directory", "")
            self.filename = option.get("filename", "")
            self.size = option.get("size", None)
            self.media_type = option.get("media_type", None)
            self.session = option.get("session", None)
            self.downloaded = option.get("downloaded", False)

    def __iter__(self):
        for attr, value in self.__dict__.items():
            yield attr, value


class format_attributes(object):
    def __init__(self):
        self.site_name = "{site_name}"
        self.first_letter = "{first_letter}"
        self.post_id = "{post_id}"
        self.media_id = "{media_id}"
        self.profile_username = "{profile_username}"
        self.model_username = "{model_username}"
        self.api_type = "{api_type}"
        self.media_type = "{media_type}"
        self.filename = "{filename}"
        self.value = "{value}"
        self.text = "{text}"
        self.date = "{date}"
        self.ext = "{ext}"

    def whitelist(self, wl: list[str]):
        new_wl: list[str] = []
        new_format_copied = copy.deepcopy(self)
        for _key, value in new_format_copied:
            if value not in wl:
                new_wl.append(value)
        return new_wl

    def __iter__(self):
        for attr, value in self.__dict__.items():
            yield attr, value


# Legacy .db and .json files
# We'll just merge things together based on their api_type
# create_metadata fixes metadata automatically
async def legacy_metadata_fixer(
    new_metadata_filepath: Path, legacy_metadata_filepaths: list[Path]
) -> tuple[create_metadata, list[Path]]:
    delete_legacy_metadatas: list[Path] = []
    new_format: list[dict[str, Any]] = []
    new_metadata_set = main_helper.import_json(new_metadata_filepath)
    for legacy_metadata_filepath in legacy_metadata_filepaths:
        if (
            legacy_metadata_filepath == new_metadata_filepath
            or not legacy_metadata_filepath.exists()
        ):
            continue
        api_type = legacy_metadata_filepath.stem
        legacy_metadata_json = main_helper.import_json(legacy_metadata_filepath)
        legacy_metadata = create_metadata(
            legacy_metadata_json, api_type=api_type
        ).convert()
        new_format.append(legacy_metadata)
        if legacy_metadata_json:
            delete_legacy_metadatas.append(legacy_metadata_filepath)
    new_metadata_object = create_metadata(new_metadata_set)
    old_metadata_set = dict(api_helper.merge_dictionaries(new_format))
    old_metadata_object = create_metadata(old_metadata_set)
    results = new_metadata_object.compare_metadata(old_metadata_object)
    return results, delete_legacy_metadatas
