
import copy

import dill


class CustomJob:
    def __init__(self, job_type:str,api_type:str) -> None:
        self.title = f"{job_type}: {api_type}"
        self.type = job_type
        self.api_type = api_type
        self.media_types:list[str] = []
        self.min = 0
        self.task = None
        self.result = []
        self.done = False
    def add_media_type(self,media_type:str):
        self.media_types.append(media_type)
    def convert_to_dill(self):
        old = copy.copy(self)
        delattr(old, "task")
        data_string: bytes = dill.dumps(old)  # type: ignore
        return data_string,old
        

        