from datetime import datetime


class HighlightModel:
    def __init__(self, option={}) -> None:
        self.id: int = option.get("id")
        self.userId: int = option.get("userId")
        self.title: str = option.get("title")
        self.coverStoryId: int = option.get("coverStoryId")
        self.cover: str = option.get("cover")
        self.storiesCount: int = option.get("storiesCount")
        self.created_at: datetime = datetime.fromtimestamp(option.get("createdAt"))
        self.updated_at: datetime = datetime.fromtimestamp(option.get("updatedAt"))
        self.stories: list = option.get("stories")
