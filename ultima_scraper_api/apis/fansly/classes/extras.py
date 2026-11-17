import copy
from pathlib import Path
from typing import Any


class ErrorDetails:
    def __init__(self, result: dict[str, Any]) -> None:
        error = result.get("error", result)
        self.code = error.get("code", 0)
        # Fansly answers {"code": 99, "details": "..."}; transport errors carry "message".
        self.message = error.get("message") or error.get("details") or ""

    async def format(self, extras: dict[str, Any]):
        match self.code:
            case 0:
                match self.message:
                    case "User not found":
                        link = Path(extras["link"])
                        self.message = f"{link.name} not found"
                    case _:
                        pass
            case _:
                pass
        return self


class AuthDetails:
    def __init__(
        self,
        id: int | None = None,
        username: str = "",
        authorization: str = "",
        user_agent: str = "",
        email: str = "",
        password: str = "",
        proxy_url: str | None = None,
        hashed: bool = False,
        support_2fa: bool = True,
        active: bool | None = None,
    ) -> None:
        self.id = id
        self.username = username
        self.authorization = authorization
        self.user_agent = user_agent
        self.email = email
        self.password = password
        self.proxy_url = proxy_url
        self.hashed = hashed
        self.support_2fa = support_2fa
        self.active = active

    def upgrade_legacy(self, options: dict[str, Any]):
        return self

    def export(self, model: Any = None):
        new_dict = copy.copy(self.__dict__)
        if model:
            for att in new_dict.copy():
                if att not in model.__annotations__:
                    del new_dict[att]
            new_dict["user_id"] = new_dict["id"]
            del new_dict["id"]
        return new_dict

