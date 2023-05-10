from __future__ import annotations

import copy
from typing import TYPE_CHECKING

import dill
from ultima_scraper_api.managers.job_manager.jobs.custom_job import CustomJob

if TYPE_CHECKING:
    import ultima_scraper_api.apis.fansly.classes as fansly_classes
    import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes

    auth_types = (
        onlyfans_classes.auth_model.create_auth | fansly_classes.auth_model.create_auth
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


class StreamlinedUser:
    def __init__(self, authed: auth_types) -> None:
        self.__authed = authed
        self.jobs: list[CustomJob] = []
        self.job_whitelist: list[int | str] = []
        self.scrape_whitelist: list[int | str] = []
        self.active: bool = True

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

    def convert_to_dill(self):
        old = copy.copy(self)
        delattr(old, "_StreamlinedUser__authed")
        delattr(old, "__raw__")
        delattr(old, "directory_manager")
        delattr(old, "file_manager")
        delattr(old, "temp_scraped")
        delattr(old, "scraped")
        old.jobs = [x.convert_to_dill()[1] for x in old.jobs]
        data_string: bytes = dill.dumps(old)  # type: ignore
        return data_string

    def get_session_manager(self):
        return self.__authed.session_manager

    def get_api(self):
        return self.__authed.api

    def is_active(self):
        return self.active
