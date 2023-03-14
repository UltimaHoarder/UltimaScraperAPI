from typing import Any


class create_highlight:
    def __init__(self, option: dict[str, Any]) -> None:
        self.id: int = option["id"]
        self.userId: int = option["userId"]
        self.title: str = option["title"]
        self.coverStoryId: int = option["coverStoryId"]
        self.cover: str = option["cover"]
        self.storiesCount: int = option["storiesCount"]
        self.createdAt: str = option["createdAt"]
