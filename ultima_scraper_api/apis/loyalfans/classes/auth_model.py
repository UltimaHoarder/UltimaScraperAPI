from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.auth_streamliner import StreamlinedAuth
from ultima_scraper_api.apis.loyalfans.classes import subscription_model
from ultima_scraper_api.apis.loyalfans.classes.extras import endpoint_links
from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.authenticator import (
        LoyalFansAuthenticator,
    )
    from ultima_scraper_api.apis.loyalfans.classes.extras import AuthDetails
    from ultima_scraper_api.apis.loyalfans.classes.user_model import LoyalFansAPI


class LoyalFansAuthModel(
    StreamlinedAuth["LoyalFansAuthenticator", "LoyalFansAPI", "AuthDetails"]
):
    def __init__(
        self,
        authenticator: "LoyalFansAuthenticator",
    ) -> None:
        self.api = authenticator.api
        self.users: dict[int, UserModel] = {}
        super().__init__(authenticator)
        self.user = authenticator.create_user(self)
        self.id = self.user.id
        self.username = self.user.username
        self.guest = self.authenticator.guest
        self.update()

    def find_user(self, identifier: int | str):
        if isinstance(identifier, int):
            user = self.users.get(identifier)
        else:
            for user in self.users.values():
                if user.username.lower() == identifier.lower():
                    break
            else:
                user = None
        return user

    def resolve_user(self, user_dict: dict[str, Any]):
        user = None
        if "id" in user_dict:
            user = self.find_user(user_dict["id"])
        if not user:
            user = UserModel(user_dict, self)
        return user

    def add_user(self, user: UserModel):
        self.users[user.id] = user

    def update(self):
        if self.user:
            identifier = self.user.id
            username = self.user.username
            self.id = identifier
            self.username = username
            # # This affects scripts that use the username to select profiles
            auth_details = self.get_auth_details()
            auth_details.id = identifier
            # auth_details.username = username

    async def get_user(self, identifier: str, refresh: bool = False):
        link = f"https://www.loyalfans.com/api/v2/profile/star/{identifier}?ngsw-bypass=true"
        response = await self.auth_session.json_request(link)
        user = UserModel(response["data"], self)
        return user

    async def get_subscription_count(self) -> dict[str, Any]:

        url = endpoint_links().subscription_count()
        payload: dict[str, Any] = {"page": 1, "search_term": "", "limit": 16}
        result = await self.auth_session.json_request(
            url, method="POST", payload=payload
        )
        return result

    async def get_subscriptions(self, limit: int | None = None) -> list[dict[str, Any]]:
        max_pagination_limit = 100  # maximum number of results per request
        if self.guest:
            return []
        subscriptions_count = await self.get_subscription_count()
        subscription_type_count: int = subscriptions_count["user_lists"][1][
            "user_count"
        ]
        limit = limit if limit else subscription_type_count
        limit = 1
        payload: dict[str, Any] = {
            "id": "subscribed",
            "page": 1,
            "limit": max_pagination_limit,
        }
        url = endpoint_links().list_subscriptions()
        urls, payloads = endpoint_links().create_payloads(
            url,
            payload,
            limit,
            pagination_limit=max_pagination_limit,
        )
        subscription_responses = await self.auth_session.bulk_json_requests(
            urls, payloads=payloads, method="POST"
        )
        subscriptions: list[dict[str, Any]] = []
        for subscription in subscription_responses:
            for user in subscription["users"]:
                subscription_status = user["subscription_status"]
                subscriptions.append(subscription_status)

        return subscriptions
