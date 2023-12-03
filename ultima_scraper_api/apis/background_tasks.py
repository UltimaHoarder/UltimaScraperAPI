import asyncio
import threading
from typing import Any, Optional


class BackgroundTask:
    def __init__(self) -> None:
        self.tasks = []
        self.queue: asyncio.Queue[Any] = asyncio.Queue()
        self.thread: Optional[threading.Thread] = None

    def worker(self, work: Any, args: Any):
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        new_loop.run_until_complete(work(args))
        return

    def create_background_task(self, function: Any, args: Any = None):
        self.thread = threading.Thread(target=self.worker, args=(function, args))
        self.thread.start()
        pass
