from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from ultima_scraper_api.apis.onlyfans.classes.auth_model import OnlyFansAuthModel


def _auth(response: object):
    return SimpleNamespace(
        user=SimpleNamespace(update_from_dict=Mock()),
        auth_session=SimpleNamespace(json_request=AsyncMock(return_value=response)),
    )


@pytest.mark.asyncio
async def test_get_me_fetches_the_accounts_own_profile_again() -> None:
    auth = _auth({"id": 1, "creditBalance": 52.14})

    user = await OnlyFansAuthModel.get_me(auth)

    # The profile kept from login is updated with the balance after a top-up.
    auth.auth_session.json_request.assert_awaited_once_with("https://onlyfans.com/api2/v2/users/me")
    auth.user.update_from_dict.assert_called_once_with({"id": 1, "creditBalance": 52.14})
    assert user is auth.user


@pytest.mark.asyncio
async def test_get_me_keeps_the_profile_when_the_site_answers_an_error() -> None:
    auth = _auth({"error": {"code": 401, "message": "Unauthorized"}})

    assert await OnlyFansAuthModel.get_me(auth) is None
    auth.user.update_from_dict.assert_not_called()
