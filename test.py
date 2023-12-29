import asyncio
from pathlib import Path

import ultima_scraper_api
from ultima_scraper_api import FanslyAPI, OnlyFansAPI, UltimaScraperAPIConfig

FULL_TEST = False


import inflection
import orjson

from ultima_scraper_api.apis.fansly.classes.user_model import create_user

# def convert_to_snake_case():
#     # json = orjson.loads(Path("test.json").read_bytes())
#     # me_json, performer_json = json[0], json[1]
#     # missing_keys = set(me_json.keys()) - set(performer_json.keys())
#     file_path = "ultima_scraper_api/apis/fansly/classes/user_model.py"
#     abc = vars(create_user({"avatar": ""}, {}))
#     with open(file_path, "r") as file:
#         file_lines = file.readlines()
#         for key in abc:
#             underscore_key = inflection.underscore(key)
#             old_string = f"self.{key}:"
#             new_string = f"self.{underscore_key}:"
#             for i, line in enumerate(file_lines):
#                 if old_string in line:
#                     line = file_lines[i]
#                     new_line = line.replace(old_string, new_string)
#                     file_lines[i] = new_line
#                     break
#         with open(file_path, "w") as file:
#             file.writelines(file_lines)


async def custom_auth(api: OnlyFansAPI):
    import orjson

    auth_path = Path("auth.json")
    _auth_json = orjson.loads(auth_path.read_bytes())
    authed = await api.login(_auth_json["auth"])
    return authed


async def main():
    async def authenticate(api: OnlyFansAPI):
        """
        Authenticates the API using the provided OnlyFansAPI instance.

        Parameters:
            api (OnlyFansAPI): An instance of the OnlyFansAPI class.

        Returns:
            Tuple: A tuple containing the authenticated API instance and the guest authentication status.
        """
        authed = None
        guest_authed = await api.login(guest=True)
        return authed, guest_authed

    async def get_all_posts(authed: ultima_scraper_api.auth_types):
        """
        Retrieves all posts from the authenticated user's account.

        Parameters:
        - authed (ultima_scraper_api.auth_types): An instance of the authentication class.

        Returns:
        - list: A list of all posts from the user's account.
        """
        user = await authed.get_user("onlyfans")
        if isinstance(user, ultima_scraper_api.user_types):
            return await user.get_posts()

    async def bulk_ip(authed: ultima_scraper_api.auth_types):
        """
        Perform bulk IP requests using the provided authenticated session.

        Args:
            authed (ultima_scraper_api.auth_types): The authenticated session.

        Returns:
            None
        """
        url = "https://checkip.amazonaws.com"
        urls = [url] * 100
        responses = await authed.auth_session.bulk_requests(urls)
        for response in responses:
            if response:
                print(await response.read())

    async def rate_limit_enabler(authed: ultima_scraper_api.auth_types):
        """
        Enables rate limiting for the given authenticated session.

        Args:
            authed (ultima_scraper_api.auth_types): The authenticated session.

        Returns:
            None
        """
        url = "https://onlyfans.com/api2/v2/init"
        urls = [url] * 10000
        responses = await authed.auth_session.bulk_json_requests(urls)
        has_errors = any("error" in item for item in responses)
        assert has_errors == False

    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    authed, _guest_authed = await authenticate(api)
    assert _guest_authed
    authed = _guest_authed
    await rate_limit_enabler(authed)
    if FULL_TEST:
        await bulk_ip(authed)
        await rate_limit_enabler(authed)

    posts = await get_all_posts(authed)
    if posts:
        for post in posts:
            if not post.text:
                continue
            author = post.get_author()
            print(f"User: {author.username}\nContent: {post.text}")
            break
    await api.close_pools()


asyncio.run(main())
