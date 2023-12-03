from __future__ import annotations

import inspect
from argparse import Namespace
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing.pool import Pool
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import urlparse

from mergedeep.mergedeep import Strategy, merge  # type: ignore

import ultima_scraper_api

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
    return results


async def get_function_name(
    function_that_called: str = "", convert_to_api_type: bool = False
):
    if not function_that_called:
        function_that_called = inspect.stack()[1].function
    if convert_to_api_type:
        return function_that_called.split("_")[-1].capitalize()
    return function_that_called


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
    final_results = [x for x in final_results if "error" not in x]
    if wrapped and final_results:
        final_results = final_results[0]
    return final_results


async def extract_list(result: dict[str, Any]):
    return result["list"]
