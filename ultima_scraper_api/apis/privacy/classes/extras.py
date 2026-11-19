import copy
from typing import Any


class ErrorDetails:
    def __init__(self, result: dict[str, Any]) -> None:
        # The API answers {"code": 401, "message": "Invalid Token"}; transport
        # errors arrive as {"error": {"code", "message"}}.
        error = result.get("error", result)
        self.code = error.get("code", 0)
        self.message = error.get("message") or ""

    async def format(self, extras: dict[str, Any]):
        return self


class AuthDetails:
    """``authorization`` is the API token (a JWT, with or without "Bearer ").

    It is what the site's own pages send to service.privacy.com.br and expires
    within hours; the site renews it server-side, which this API cannot do.
    """

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

    @property
    def token(self) -> str:
        return self.authorization.removeprefix("Bearer ").strip()

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
