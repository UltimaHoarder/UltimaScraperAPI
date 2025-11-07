from enum import Enum

from ultima_scraper_api.apis.loyalfans.classes.extras import Any


class ToastTypeEnum(str, Enum):
    SUBSCRIBED = "subscribed"
    MESSAGE = "message"


class ToastDataCodeEnum(str, Enum):
    NEW_SUBSCRIBER = "new_subscriber"
    NEW_SUBSCRIBER_TRIAL = "new_subscriber_trial"
    NEW_STREAM = "new_stream"
    NEW_COMMENT = "new_comment"
    PRICE_CHANGED_FROM_FREE = "price_changed_from_free"
    PRICE_CHANGED_NOT_FROM_FREE = "price_changed_not_from_free"


class ToastCollectionModel:
    def __init__(self, options: list[dict[str, Any]]) -> None:
        self.toasts: list[ToastModel] = []
        for option in options:
            self.toasts.append(ToastModel(option))

    def find(
        self, toast_type: str | None = None, toast_data_code: str | None = None
    ) -> list["ToastModel"]:
        return [
            toast
            for toast in self.toasts
            if (not toast_type or toast.type == toast_type)
            and (not toast_data_code or toast.data.code == toast_data_code)
        ]


class ToastModel:
    def __init__(self, option: dict[str, Any]) -> None:
        self.id: int = option["id"]
        self.type: str = option["type"]
        self.title: str = option["title"]
        self.text: str = option["text"]
        self.data: ToastDataModel = ToastDataModel(option["data"])


class ToastDataModel:
    def __init__(self, option: dict[str, Any]) -> None:
        self.code: str = option["code"]
        self.related_user: dict[str, Any] = option["relatedUser"]
        self.replacements: dict[str, Any] = option["replacements"]
        self.template: str = option["template"]
