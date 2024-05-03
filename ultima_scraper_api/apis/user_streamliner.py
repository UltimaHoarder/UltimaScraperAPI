from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from ultima_scraper_api.managers.job_manager.jobs.custom_job import CustomJob
from ultima_scraper_api.managers.session_manager import AuthedSession, SessionManager

if TYPE_CHECKING:
    import ultima_scraper_api.apis.fansly.classes as fansly_classes
    import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes

    auth_types = (
        onlyfans_classes.auth_model.OnlyFansAuthModel
        | fansly_classes.auth_model.FanslyAuthModel
    )


class JobTask:
    def __init__(self, title: str) -> None:
        self.title = title
        self.child_tasks: list[JobTask] = []
        self.min = 0
        self.max = 0
        self.done = False

    def advance(self, length: int):
        self.min += length


class Job:
    def __init__(self, title: str) -> None:
        self.title = title
        self.done = False
        self.added = False
        self.tasks: list[JobTask] = []

    def create_task(self, title: str):
        task = JobTask(title)
        self.tasks.append(task)
        return task

    def create_tasks(self, data: list[str]):
        for key in data:
            self.create_task(key)

    def get_current_task(self):
        tasks = [x for x in self.tasks if not x.done]
        return None if not tasks else tasks[0]


class Cache:
    def __init__(self) -> None:
        from ultima_scraper_api.apis.auth_streamliner import CacheStats

        self.posts = CacheStats()
        self.messages = CacheStats()


T = TypeVar("T")
TAPI = TypeVar("TAPI")


class StreamlinedUser(Generic[T, TAPI]):
    def __init__(self, authed: T) -> None:
        self.__authed = authed
        self.cache = Cache()
        self.jobs: list[CustomJob] = []
        self.job_whitelist: list[int | str] = []
        self.scrape_whitelist: list[int | str] = []
        self.active: bool = True
        self.aliases: list[str] = []

    def get_authed(self):
        return self.__authed

    def get_job(self, value: str):
        found_jobs = [x for x in self.jobs if x.title == value]
        found_job = None
        if found_jobs:
            found_job = found_jobs[0]
        return found_job

    def get_complete_jobs(self):
        return [x for x in self.jobs if x.done == True]

    def get_incomplete_jobs(self):
        return [x for x in self.jobs if x.done == False]

    def get_current_job(self):
        incomplete_jobs = self.get_incomplete_jobs()
        return None if not incomplete_jobs else incomplete_jobs[0]

    def get_requester(self) -> AuthedSession:
        return self.__authed.auth_session  # type: ignore

    def get_session_manager(self) -> SessionManager:
        return self.__authed.auth_session.get_session_manager()  # type: ignore

    def get_api(self) -> TAPI:
        return self.__authed.get_api()  # type: ignore

    def is_active(self):
        return self.active

    def get_usernames(self, ignore_id: bool = True) -> list[str]:
        final_usernames: list[str] = [self.username]  # type: ignore
        for alias in self.get_aliases(ignore_id=ignore_id):
            if alias not in final_usernames:
                final_usernames.append(alias)
        if ignore_id and len(final_usernames) > 1:
            invalid_usernames = [f"u{self.id}"]  # type: ignore
            for invalid_username in invalid_usernames:
                if invalid_username in final_usernames:
                    final_usernames.remove(invalid_username)
        assert final_usernames
        return final_usernames

    def get_aliases(self, ignore_id: bool = True):
        final_aliases = self.aliases.copy()
        if ignore_id:
            invalid_aliases = [f"u{self.id}"]  # type: ignore
            for invalid_alias in invalid_aliases:
                if invalid_alias in final_aliases:
                    final_aliases.remove(invalid_alias)
        return final_aliases

    def add_aliases(self, aliases: list[str]):
        for alias in aliases:
            if alias == self.username:
                continue
            if alias not in self.aliases:
                self.aliases.append(alias)
