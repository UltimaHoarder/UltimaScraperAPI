import asyncio
import copy
import functools
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Type, TypeVar

import orjson
import requests
import ultima_scraper_api
import ultima_scraper_api.classes.prepare_webhooks as prepare_webhooks
from aiofiles import os as async_os
from alive_progress import alive_bar  # type: ignore
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from mergedeep import Strategy, merge  # type: ignore

if TYPE_CHECKING:
    api_types = ultima_scraper_api.api_types
    auth_types = ultima_scraper_api.auth_types


os_name = platform.system()


try:
    from psutil import disk_usage
except ImportError:
    import errno
    from collections import namedtuple

    # https://github.com/giampaolo/psutil/blob/master/psutil/_common.py#L176
    sdiskusage = namedtuple("sdiskusage", ["total", "used", "free", "percent"])

    # psutil likes to round the disk usage percentage to 1 decimal
    # https://github.com/giampaolo/psutil/blob/master/psutil/_common.py#L365
    def disk_usage(path: str, round_: int = 1):
        # check if path exists
        if not os.path.exists(path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)

        # on POSIX systems you can pass either a file or a folder path
        # Windows only allows folder paths
        if not os.path.isdir(path):
            path = os.path.dirname(path)

        if os_name == "Windows":
            import ctypes

            total_bytes = ctypes.c_ulonglong(0)
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(path),
                None,
                ctypes.pointer(total_bytes),
                ctypes.pointer(free_bytes),
            )
            return sdiskusage(
                total_bytes.value,
                total_bytes.value - free_bytes.value,
                free_bytes.value,
                round(
                    (total_bytes.value - free_bytes.value) * 100 / total_bytes.value,
                    round_,
                ),
            )
        else:  # Linux, Darwin, ...
            st = os.statvfs(path)
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            used = total - free
            return sdiskusage(total, used, free, round(100 * used / total, round_))


def clean_text(string: str, remove_spaces: bool = False):
    try:
        import lxml as unused_lxml_  # type: ignore

        html_parser = "lxml"
    except ImportError:
        html_parser = "html.parser"
    matches = ["\n", "<br>"]
    for m in matches:
        string = string.replace(m, " ").strip()
    string = " ".join(string.split())
    string = BeautifulSoup(string, html_parser).get_text()
    SAFE_PTN = r"[|\^&+\-%*/=!:\"?><]"
    string = re.sub(SAFE_PTN, " ", string.strip()).strip()
    if remove_spaces:
        string = string.replace(" ", "_")
    return string


async def format_media_set(media_set: list[dict[str, Any]]):
    merged: dict[str, Any] = merge({}, *media_set, strategy=Strategy.ADDITIVE)
    if "directories" in merged:
        for directory in merged["directories"]:
            await async_os.makedirs(directory, exist_ok=True)
        merged.pop("directories")
    return merged


async def format_file(filepath: Path, timestamp: float, reformat_media: bool):
    if reformat_media:
        while True:
            if os_name == "Windows":
                from win32_setctime import setctime

                setctime(filepath, timestamp)
                # print(f"Updated Creation Time {filepath}")
            await asyncio.to_thread(os.utime, filepath, (timestamp, timestamp))
            # print(f"Updated Modification Time {filepath}")
            break


def prompt_modified(message: str, path: Path | None = None):
    input(message)
    return
    # Need to move this to an edit config function (tired of all the pop ups)
    editor = shutil.which(
        os.environ.get("EDITOR", "notepad" if os_name == "Windows" else "nano")
    )
    if editor:
        print(message)
        subprocess.run([editor, path], check=True)
    else:
        input(message)


def import_json(json_path: Path):
    with json_path.open(encoding="utf-8") as o_file:
        json_file = orjson.loads(o_file.read())
        return json_file


def export_json(data: list[Any] | dict[str, Any], filepath: Path):
    if filepath.suffix:
        filepath.parent.mkdir(exist_ok=True)
    filepath.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))


def object_to_json(item: Any):
    _json = orjson.loads(item.json())
    return _json


T = TypeVar("T")


def get_config(config_path: Path, config_class: Type[T]) -> tuple[T, bool]:
    json_config = import_json(config_path)
    if "supported" in json_config:
        config_path.rename(config_path.parent.joinpath("old_config.json"))
    old_json_config = copy.deepcopy(json_config)
    new_json_config = old_json_config
    converted_object = config_class(**new_json_config)
    new_json_config = object_to_json(converted_object)
    updated = True if json_config else False
    status = "updated" if updated else "created"
    if new_json_config != old_json_config:
        export_json(new_json_config, config_path)
        prompt_modified(
            f"The {config_path} file has been {status}. Fill in whatever you need to fill in and then press enter when done.\n",
        )

    return converted_object, updated


from ultima_scraper_api.config import Settings


def open_partial(path: Path) -> BinaryIO:
    prefix, extension = os.path.splitext(path)
    while True:
        partial_path = f"{prefix}{extension}.part"
        return open(partial_path, "wb")


async def send_webhook(
    item: "auth_types",
    webhook_hide_sensitive_info: bool,
    webhook_links: list[str],
    category: str,
    category2: str,
):
    if category == "auth_webhook":
        for webhook_link in webhook_links:
            auth = item
            username = auth.username
            if webhook_hide_sensitive_info:
                username = "REDACTED"
            message = prepare_webhooks.discord()
            embed = message.embed()
            embed.title = f"Auth {category2.capitalize()}"
            embed.add_field("username", username)
            message.embeds.append(embed)
            message = orjson.loads(json.dumps(message, default=lambda o: o.__dict__))
            requests.post(webhook_link, json=message)
    if category == "download_webhook":
        subscriptions = await item.get_subscriptions()
        for subscription in subscriptions:
            if await subscription.user.if_scraped():
                for webhook_link in webhook_links:
                    message = prepare_webhooks.discord()
                    embed = message.embed()
                    embed.title = f"Downloaded: {subscription.username}"
                    embed.add_field("username", subscription.username)
                    embed.add_field("post_count", subscription.user.posts_count)
                    embed.add_field("link", subscription.user.get_link())
                    embed.image.url = subscription.user.avatar
                    message.embeds.append(embed)
                    message = orjson.loads(
                        json.dumps(message, default=lambda o: o.__dict__)
                    )
                    requests.post(webhook_link, json=message)


def find_between(s: str, start: str, end: str):
    format = f"{start}(.+?){end}"
    x = re.search(format, s)
    if x:
        x = x.group(1)
    else:
        x = s
    return x


def extract_string_between_characters(text: str, opening_char: str, closing_char: str):
    pattern = re.escape(opening_char) + r"(.*?)" + re.escape(closing_char)
    matches = re.findall(pattern, text)
    return matches


def module_chooser(domain: str, json_sites: dict[str, Any]):
    string = "Select Site: "
    separator = " | "
    site_names: list[str] = []
    wl = ["onlyfans", "fansly"]
    bl = []
    site_count = len(json_sites)
    count = 0
    for x in json_sites:
        if not wl:
            if x in bl:
                continue
        elif x not in wl:
            continue
        string += str(count) + " = " + x
        site_names.append(x)
        if count + 1 != site_count:
            string += separator

        count += 1
    if domain and domain not in site_names:
        string = f"{domain} not supported"
        site_names = []
    return string, site_names


async def replace_path(old_string: str, new_string: str, path: Path):
    return Path(path.as_posix().replace(old_string, new_string))


def get_current_month_dates():
    current_date = datetime.today()
    first_day = current_date.replace(day=1)
    last_day = first_day + relativedelta(months=1, days=-1)
    return first_day, last_day


def get_date_range_past_days(days: int = 31):
    current_date = datetime.today()
    first_day = current_date - timedelta(days=days)
    return first_day, current_date


def date_between_custom_range(
    date_value: datetime, start_date: datetime, end_date: datetime
):
    if start_date < date_value < end_date:
        return True
    else:
        return False


def date_between_cur_month(date_value: datetime):
    current_date = datetime.today()
    first_day = current_date.replace(day=1)
    last_day = first_day + relativedelta(months=1, days=-1)
    if first_day.date() < date_value.date() < last_day.date():
        return True
    else:
        return False


def split_string(identifiers: str):
    result = re.split(r"[,\n]", identifiers)

    split_identifiers = [s.strip() for s in result]
    return split_identifiers


def is_pascal_case(s: str):
    # Check if the string is not empty and starts with an uppercase letter
    if s and s[0].isupper():
        # Check if the string contains only letters and digits
        return all(c.isupper() or c.islower() or c.isdigit() for c in s)
    return False


class ProgressBar:
    def __init__(self, title: str = ""):
        self.title = title

    async def gather(self, tasks: list[asyncio.Task[Any]]):
        def increment(method: Any, _task: Any):
            method()

        with alive_bar(len(tasks)) as bar:  # type:ignore
            bar.title(self.title)  # type:ignore
            for task in tasks:
                task.add_done_callback(functools.partial(increment, bar))
            await asyncio.gather(*tasks)
        return [task.result() for task in tasks]
