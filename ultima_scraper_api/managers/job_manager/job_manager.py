import asyncio
import copy
from typing import Any

import ultima_scraper_api
from ultima_scraper_api.managers.job_manager.jobs.custom_job import CustomJob

api_types = ultima_scraper_api.api_types

user_types = ultima_scraper_api.user_types


class JobManager:
    def __init__(self) -> None:
        self.jobs: list[CustomJob] = []
        self.queue: asyncio.Queue[Any] = asyncio.Queue()
        self.worker_task = asyncio.create_task(self.worker())

    def create_jobs(
        self, value: str, type_values: list[str], module: Any, module_args: list[Any]
    ):
        local_jobs: list[CustomJob] = []
        for type_value in type_values:
            local_args = copy.copy(module_args)
            match value:
                case "Scrape":
                    job = CustomJob(value, type_value)
                    local_args.append(type_value)
                    job.task = module(*local_args)
                case "Download":
                    job = CustomJob(value, type_value)
                    local_args.append(type_value)
                    job.task = module(*local_args)
                case _:
                    job = None
            if job:
                local_jobs.append(job)
        self.jobs.extend(local_jobs)
        return local_jobs

    def add_media_type_to_jobs(self, media_type: str | list[str]):
        if isinstance(media_type, str):
            media_type = [media_type]
        [job.add_media_type(mt) for job in self.jobs for mt in media_type]

    async def worker(self):
        while True:
            job = await self.queue.get()
            # We can make jobs work in the background if we make waiting for inputs async
            await job.task

            self.queue.task_done()

            # print(f'{job.type} has been processed')