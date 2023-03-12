from __future__ import annotations

import asyncio
import copy
import json
import math
import os
import platform
import random
import re
import secrets
import shutil
import string
import subprocess
from datetime import datetime
from itertools import zip_longest
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Literal, Optional, Union

import orjson
import requests
from aiofiles import os as async_os
from aiohttp.client import ClientSession
from aiohttp.client_reqrep import ClientResponse
from aiohttp_socks.connector import ProxyConnector
from bs4 import BeautifulSoup
from mergedeep import Strategy, merge

import ultima_scraper_api
import ultima_scraper_api.classes.make_settings as make_settings
import ultima_scraper_api.classes.prepare_webhooks as prepare_webhooks
from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.dashboard_controller_api import DashboardControllerAPI
from ultima_scraper_api.apis.fansly import fansly as Fansly
from ultima_scraper_api.apis.onlyfans import onlyfans as OnlyFans
from ultima_scraper_api.database.databases.user_data.models.media_table import (
    template_media_table,
)

if TYPE_CHECKING:
    from ultima_scraper_api.classes.prepare_directories import DirectoryManager
    from ultima_scraper_api.managers.storage_managers.filesystem_manager import (
        FilesystemManager,
    )

auth_types = ultima_scraper_api.auth_types
user_types = ultima_scraper_api.user_types


os_name = platform.system()

if os_name == "Windows":
    import ctypes

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


def getfrozencwd():
    import sys

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    else:
        return os.getcwd()


def parse_links(site_name, input_link):
    if site_name in {"onlyfans", "fansly"}:
        username = input_link.rsplit("/", 1)[-1]
        return username

    if site_name in {"patreon", "fourchan", "bbwchan"}:
        if "catalog" in input_link:
            input_link = input_link.split("/")[1]
            print(input_link)
            return input_link
        if input_link[-1:] == "/":
            input_link = input_link.split("/")[3]
            return input_link
        if "4chan.org" not in input_link:
            return input_link


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


async def format_image(filepath: str, timestamp: float, reformat_media: bool):
    if reformat_media:
        while True:
            try:
                if os_name == "Windows":
                    from win32_setctime import setctime

                    setctime(filepath, timestamp)
                    # print(f"Updated Creation Time {filepath}")
                os.utime(filepath, (timestamp, timestamp))
                # print(f"Updated Modification Time {filepath}")
            except Exception as e:
                continue
            break


async def async_downloads(
    download_list: list[template_media_table],
    subscription: user_types,
    global_settings: make_settings.Settings,
):
    async def run(download_list: list[template_media_table]):
        session_m = subscription.get_session_manager()
        filesystem_manager = subscription.get_api().filesystem_manager
        proxies = session_m.proxies
        proxy = (
            session_m.proxies[random.randint(0, len(proxies) - 1)] if proxies else ""
        )
        connector = ProxyConnector.from_url(proxy) if proxy else None
        final_cookies: dict[Any, Any] = (
            session_m.auth.auth_details.cookie.format() if session_m.use_cookies else {}
        )
        async with ClientSession(
            connector=connector,
            cookies=final_cookies,
            read_timeout=None,
        ) as session:
            tasks = []
            # Get content_lengths
            for download_item in download_list:
                link = download_item.link
                if link:
                    task = asyncio.ensure_future(
                        session_m.json_request(
                            download_item.link,
                            session,
                            method="HEAD",
                            json_format=False,
                        )
                    )
                    tasks.append(task)
            responses = await asyncio.gather(*tasks)
            tasks.clear()

            async def check(
                download_item: template_media_table, response: ClientResponse
            ):
                filepath = os.path.join(download_item.directory, download_item.filename)
                response_status = False
                if response.status == 200:
                    response_status = True
                    if response.content_length:
                        download_item.size = response.content_length

                if await async_os.path.exists(filepath):
                    if await async_os.path.getsize(filepath) == response.content_length:
                        download_item.downloaded = True
                    else:
                        return download_item
                else:
                    if response_status:
                        return download_item

            for download_item in download_list:
                if download_item.size == None:
                    download_item.size = 0
                temp_response = [
                    response
                    for response in responses
                    if response and str(response.url) == download_item.link
                ]
                if temp_response:
                    temp_response = temp_response[0]
                    task = check(download_item, temp_response)
                    tasks.append(task)
            result = await asyncio.gather(*tasks)
            download_list = [x for x in result if x]
            job = subscription.get_job("download")
            total_size = sum([x.size for x in download_list if x.id])
            tasks.clear()
            if download_list:
                # ASSIGN TOTAL DOWNLOAD SIZE TO JOBS (SOMEHOW)
                # current_task = job.get_current_task()
                # current_task.max = total_size
                pass

            async def process_download(download_item: template_media_table):
                while True:
                    result = await session_m.download_content(
                        download_item, session, subscription
                    )
                    if result:
                        response, download_item = result.values()
                        if response:
                            download_path = os.path.join(
                                download_item.directory, download_item.filename
                            )
                            status_code = await filesystem_manager.write_data(
                                response, download_path
                            )
                            if not status_code:
                                pass
                            elif status_code == 1:
                                continue
                            elif status_code == 2:
                                # total_size = (
                                #     progress_bar.tasks[0].total - download_item.size
                                # )
                                # progress_bar.update(0, total=total_size)

                                # ASSIGN TOTAL DOWNLOAD SIZE TO JOBS (SOMEHOW)
                                # current_task.max = -download_item.size
                                break
                            timestamp = download_item.created_at.timestamp()
                            await format_image(
                                download_path,
                                timestamp,
                                global_settings.helpers.reformat_media,
                            )
                            download_item.size = response.content_length
                            download_item.downloaded = True
                    break

            max_threads = api_helper.calculate_max_threads(session_m.max_threads)
            download_groups = grouper(max_threads, download_list)
            for download_group in download_groups:
                tasks = []
                for download_item in download_group:
                    task = process_download(download_item)
                    if task:
                        tasks.append(task)
                await asyncio.gather(*tasks)
            return True

    results = await asyncio.ensure_future(run(download_list))
    return results


def format_paths(j_directories, site_name):
    paths = []
    for j_directory in j_directories:
        paths.append(j_directory)
    return paths


def check_space(
    download_paths: list[Path],
    min_size: int = 0,
    priority: str = "download",
) -> Path:
    root = ""
    while not root:
        paths = []
        for download_path in download_paths:
            # ISSUE
            # Could cause problems w/ relative/symbolic links that point to another hard drive
            # Haven't tested if it calculates hard A or relative/symbolic B's total space.
            obj_Disk = disk_usage(str(download_path.parent))
            free = obj_Disk.free / (1024.0**3)
            x = {}
            x["path"] = download_path
            x["free"] = free
            paths.append(x)
        if priority == "download":
            for item in paths:
                download_path = item["path"]
                free = item["free"]
                if free > min_size:
                    root = download_path
                    break
        elif priority == "upload":
            paths.sort(key=lambda x: x["free"])
            item = paths[0]
            root = item["path"]
    return root


def find_model_directory(username, directories) -> tuple[str, bool]:
    download_path = ""
    status = False
    for directory in directories:
        download_path = os.path.join(directory, username)
        if os.path.exists(download_path):
            status = True
            break
    return download_path, status


def are_long_paths_enabled():
    if os_name != "Windows":
        return True

    ntdll = ctypes.WinDLL("ntdll")

    if not hasattr(ntdll, "RtlAreLongPathsEnabled"):
        return False

    ntdll.RtlAreLongPathsEnabled.restype = ctypes.c_ubyte
    ntdll.RtlAreLongPathsEnabled.argtypes = ()
    return bool(ntdll.RtlAreLongPathsEnabled())


def check_for_dupe_file(download_path, content_length):
    found = False
    if os.path.isfile(download_path):
        content_length = int(content_length)
        local_size = os.path.getsize(download_path)
        if local_size == content_length:
            found = True
    return found


def prompt_modified(message: str, path: Path):
    editor = shutil.which(
        os.environ.get("EDITOR", "notepad" if os_name == "Windows" else "nano")
    )
    if editor:
        print(message)
        subprocess.run([editor, path], check=True)
    else:
        input(message)


def import_json(json_path: Path):
    json_file: dict[str, Any] = {}
    if json_path.exists() and json_path.stat().st_size and json_path.suffix == ".json":
        with json_path.open(encoding="utf-8") as o_file:
            json_file = orjson.loads(o_file.read())
    return json_file


def export_json(metadata: list[Any] | dict[str, Any], filepath: Path):
    if filepath.suffix:
        filepath.parent.mkdir(exist_ok=True)
    filepath.write_bytes(orjson.dumps(metadata, option=orjson.OPT_INDENT_2))


def object_to_json(item: Any):
    _json = orjson.loads(orjson.dumps(item, default=lambda o: o.__dict__))
    return _json


def get_config(config_path: Path) -> tuple[make_settings.Config, bool]:
    json_config = import_json(config_path)
    old_json_config = copy.deepcopy(json_config)
    new_json_config = make_settings.fix(json_config)
    converted_object = make_settings.Config(**new_json_config)
    new_json_config = object_to_json(converted_object.export())
    updated = False
    if new_json_config != old_json_config:
        export_json(new_json_config, config_path)
        if json_config:
            updated = True
            prompt_modified(
                f"The {config_path} file has been updated. Fill in whatever you need to fill in and then press enter when done.\n",
                config_path,
            )
        else:
            if not json_config:
                prompt_modified(
                    f"The {config_path} file has been created. Fill in whatever you need to fill in and then press enter when done.\n",
                    config_path,
                )

    return converted_object, updated


async def process_webhooks(
    api: OnlyFans.start | Fansly.start,
    category: str,
    category_2: Literal["succeeded", "failed"],
    global_settings: make_settings.Settings,
):
    webhook_settings = global_settings.webhooks
    global_webhooks = webhook_settings.global_webhooks
    final_webhooks = global_webhooks
    global_status = webhook_settings.global_status
    final_webhook_status = global_status
    webhook_hide_sensitive_info = True
    if category == "auth_webhook":
        category_webhook = webhook_settings.auth_webhook
        webhook = category_webhook.get_webhook(category_2)
        webhook_status = webhook.status
        webhook_hide_sensitive_info = webhook.hide_sensitive_info
        if webhook_status != None:
            final_webhook_status = webhook_status
        if webhook.webhooks:
            final_webhooks = webhook.webhooks
    elif webhook_settings.download_webhook:
        category_webhook = webhook_settings.download_webhook
        webhook = category_webhook.get_webhook(category_2)
        webhook_status = webhook.status
        if webhook_status != None:
            final_webhook_status = webhook_status
        webhook_hide_sensitive_info = webhook.hide_sensitive_info
        if webhook.webhooks:
            final_webhooks = webhook.webhooks
    webhook_links = final_webhooks
    if final_webhook_status:
        for auth in api.auths:
            await send_webhook(
                auth, webhook_hide_sensitive_info, webhook_links, category, category_2
            )
        print
    print


def is_me(user_api):
    if "email" in user_api:
        return True
    else:
        return False


def open_partial(path: Path) -> BinaryIO:
    prefix, extension = os.path.splitext(path)
    while True:
        partial_path = "{}-{}{}.part".format(prefix, secrets.token_hex(6), extension)
        try:
            return open(partial_path, "xb")
        except FileExistsError:
            pass


def grouper(n, iterable, fillvalue: Optional[Union[str, int]] = None):
    args = [iter(iterable)] * n
    final_grouped = list(zip_longest(fillvalue=fillvalue, *args))
    if not fillvalue:
        grouped = []
        for group in final_grouped:
            group = [x for x in group if x]
            grouped.append(group)
        final_grouped = grouped
    return final_grouped


def metadata_fixer(directory):
    archive_file = os.path.join(directory, "archive.json")
    metadata_file = os.path.join(directory, "Metadata")
    if os.path.exists(archive_file):
        os.makedirs(metadata_file, exist_ok=True)
        new = os.path.join(metadata_file, "Archive.json")
        shutil.move(archive_file, new)


def ordinal(n):
    return "%d%s" % (n, "tsnrhtdd"[(n / 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4])


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def humansize(nbytes):
    i = 0
    suffixes = ["B", "KB", "MB", "GB", "TB", "PB"]
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.0
        i += 1
    f = ("%.2f" % nbytes).rstrip("0").rstrip(".")
    return "%s %s" % (f, suffixes[i])


def byteToGigaByte(n):
    return n / math.pow(10, 9)


async def send_webhook(
    item: auth_types,
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
        subscriptions = await item.get_subscriptions(refresh=False)
        for subscription in subscriptions:
            if await subscription.if_scraped():
                for webhook_link in webhook_links:
                    message = prepare_webhooks.discord()
                    embed = message.embed()
                    embed.title = f"Downloaded: {subscription.username}"
                    embed.add_field("username", subscription.username)
                    embed.add_field("post_count", subscription.postsCount)
                    embed.add_field("link", subscription.get_link())
                    embed.image.url = subscription.avatar
                    message.embeds.append(embed)
                    message = orjson.loads(
                        json.dumps(message, default=lambda o: o.__dict__)
                    )
                    requests.post(webhook_link, json=message)


def find_between(s, start, end):
    format = f"{start}(.+?){end}"
    x = re.search(format, s)
    if x:
        x = x.group(1)
    else:
        x = s
    return x


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
