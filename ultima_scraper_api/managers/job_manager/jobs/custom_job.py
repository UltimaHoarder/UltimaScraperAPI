import copy

import dill


class CustomJob:
    def __init__(self, job_type: str, api_type: str | None = None) -> None:
        self.title = f"{job_type}: {api_type}"
        self.type = job_type
        self.api_type = api_type
        self.media_types: list[str] = []
        self.min = 0
        self.task = None
        self.result = []
        self.done = False
        self.options: list[str] = []
        self.blacklist: list[str] = []
        self.ignore: bool = False

    def add_media_type(self, media_type: str):
        if media_type in self.media_types:
            return
        self.media_types.append(media_type)
