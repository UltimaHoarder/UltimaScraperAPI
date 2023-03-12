from __future__ import annotations

import inspect
from argparse import Namespace
from itertools import chain
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing.pool import Pool
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import urlparse

from mergedeep.mergedeep import Strategy, merge  # type: ignore

import ultima_scraper_api
from ultima_scraper_api.managers.session_manager import SessionManager

if TYPE_CHECKING:
    auth_types = ultima_scraper_api.auth_types
    user_types = ultima_scraper_api.user_types
    error_types = ultima_scraper_api.error_types
parsed_args = Namespace()


class CustomPool:
    def __init__(self, max_threads: int | None = None) -> None:
        self.max_threads = max_threads

    def __enter__(self):
        max_threads = calculate_max_threads(self.max_threads)
        self.pool: Pool = ThreadPool(max_threads)
        return self.pool

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        if self.pool:
            self.pool.close()
        pass


def multiprocessing(max_threads: Optional[int] = None):
    max_threads = calculate_max_threads(max_threads)
    pool: Pool = ThreadPool(max_threads)
    return pool


def calculate_max_threads(max_threads: Optional[int] = None):
    if not max_threads:
        max_threads = -1
    max_threads2 = cpu_count()
    if max_threads < 1 or max_threads >= max_threads2:
        max_threads = max_threads2
    return max_threads


def restore_missing_data(master_set2: list[str], media_set, split_by):
    count = 0
    new_set: set[str] = set()
    for item in media_set:
        if not item:
            link = master_set2[count]
            offset = int(link.split("?")[-1].split("&")[1].split("=")[1])
            limit = int(link.split("?")[-1].split("&")[0].split("=")[1])
            if limit == split_by + 1:
                break
            offset2 = offset
            limit2 = int(limit / split_by) if limit > 1 else 1
            for item in range(1, split_by + 1):
                link2 = link.replace("limit=" + str(limit), "limit=" + str(limit2))
                link2 = link2.replace("offset=" + str(offset), "offset=" + str(offset2))
                offset2 += limit2
                new_set.add(link2)
        count += 1
    new_set = new_set if new_set else master_set2
    return list(new_set)


async def scrape_endpoint_links(
    links: list[str], session_manager: SessionManager | None
):
    media_set: list[dict[str, str]] = []
    max_attempts = 100
    for attempt in list(range(max_attempts)):
        if not links or not session_manager:
            continue
        print("Scrape Attempt: " + str(attempt + 1) + "/" + str(max_attempts))
        results = await session_manager.bulk_requests(links)
        results = [await x.json() for x in results if x]
        not_faulty = [x for x in results if x]
        faulty = [
            {"key": k, "value": v, "link": links[k]}
            for k, v in enumerate(results)
            if not v
        ]
        last_number = len(results) - 1
        if faulty:
            positives = [x for x in faulty if x["key"] != last_number]
            false_positive = [x for x in faulty if x["key"] == last_number]
            if positives:
                attempt = attempt if attempt > 1 else attempt + 1
                num = int(len(faulty) * (100 / attempt))
                split_by = 2
                print("Missing " + str(num) + " Posts... Retrying...")
                links = restore_missing_data(links, results, split_by)
                media_set.extend(not_faulty)
            if not positives and false_positive:
                media_set.extend(not_faulty)
                break
        else:
            media_set.extend(not_faulty)
            break
    if media_set and "list" in media_set[0]:
        final_media_set = list(chain(*[x["list"] for x in media_set]))
    else:
        final_media_set = list(chain(*media_set))
    return final_media_set


def calculate_the_unpredictable(
    link: str, offset: int, limit: int = 1, multiplier: int = 1, depth: int = 1
):
    final_links: list[str] = []
    final_offsets = list(range(offset, multiplier * depth * limit, limit))
    final_calc = 0
    for temp_offset in final_offsets:
        final_calc = temp_offset
        parsed_link = urlparse(link)
        q = parsed_link.query.split("&")
        offset_string = [x for x in q if "offset" in x][0]
        new_link = link.replace(offset_string, f"offset={final_calc}")
        final_links.append(new_link)
    final_links = list(reversed(list(reversed(final_links))[:multiplier]))
    return final_links, final_calc


def parse_config_inputs(custom_input: Any) -> list[str]:
    if isinstance(custom_input, str):
        custom_input = custom_input.split(",")
    return custom_input


async def handle_error_details(
    item: error_types | dict[str, Any] | list[dict[str, Any]] | list[error_types],
    remove_errors_status: bool = False,
    api_type: Optional[auth_types] = None,
):
    results = []
    if isinstance(item, list):
        if remove_errors_status and api_type:
            results = await remove_errors(item)
    else:
        # Will move to logging instead of printing later.
        print(f"Error: {item.__dict__}")
    return results


async def get_function_name(
    function_that_called: str = "", convert_to_api_type: bool = False
):
    if not function_that_called:
        function_that_called = inspect.stack()[1].function
    if convert_to_api_type:
        return function_that_called.split("_")[-1].capitalize()
    return function_that_called


async def handle_refresh(
    api: auth_types | user_types,
    api_type: str,
    refresh: bool,
    function_that_called: str,
):
    result: list[Any] = []
    # If refresh is False, get already set data
    if not api_type and not refresh:
        api_type = (
            await get_function_name(function_that_called, True)
            if not api_type
            else api_type
        )
        try:
            # We assume the class type is create_user
            result = getattr(api.temp_scraped, api_type)
        except AttributeError:
            # we assume the class type is create_auth
            api_type = api_type.lower()
            result = getattr(api, api_type)

    return result


async def default_data(
    api: auth_types | user_types, refresh: bool = False, api_type: str = ""
):
    status: bool = False
    result: list[Any] = []
    function_that_called = inspect.stack()[1].function
    auth_types = ultima_scraper_api.auth_types

    if isinstance(api, auth_types):
        # create_auth class
        auth = api
        match function_that_called:
            case function_that_called if function_that_called in [
                "get_paid_content",
                "get_chats",
                "get_lists_users",
                "get_subscriptions",
            ]:
                if not auth.active or not refresh:
                    result = await handle_refresh(
                        auth, api_type, refresh, function_that_called
                    )
                    status = True
            case "get_mass_messages":
                if not auth.active or not auth.isPerformer:
                    result = await handle_refresh(
                        auth, api_type, refresh, function_that_called
                    )
                    status = True
            case _:
                result = await handle_refresh(
                    auth, api_type, refresh, function_that_called
                )
                if result:
                    status = True
    else:
        # create_user class
        user = api
        match function_that_called:
            case "get_stories":
                if not user.hasStories:
                    result = await handle_refresh(
                        user, api_type, refresh, function_that_called
                    )
                    status = True
            case "get_messages":
                if user.is_me():
                    result = await handle_refresh(
                        user, api_type, refresh, function_that_called
                    )
                    status = True
            case function_that_called if function_that_called in [
                "get_archived_stories"
            ]:
                if not (user.is_me() and user.isPerformer):
                    result = await handle_refresh(
                        user, api_type, refresh, function_that_called
                    )
                    status = True
            case _:
                result = await handle_refresh(
                    user, api_type, refresh, function_that_called
                )
                if result:
                    status = True
    return result, status


def merge_dictionaries(items: list[dict[str, Any]]):
    final_dictionary: dict[str, Any] = merge({}, *items, strategy=Strategy.ADDITIVE)  # type: ignore
    return final_dictionary


async def remove_errors(results: Any):
    error_types = ultima_scraper_api.error_types
    final_results: list[Any] = []
    wrapped = False
    if not isinstance(results, list):
        wrapped = True
        final_results.append(results)
    else:
        final_results = results
    final_results = [x for x in final_results if not isinstance(x, error_types)]
    if wrapped and final_results:
        final_results = final_results[0]
    return final_results
