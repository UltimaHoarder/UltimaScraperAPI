import asyncio
from pathlib import Path

import ultima_scraper_api
from ultima_scraper_api import UltimaScraperAPIConfig

FULL_TEST = False


async def main():
    async def authenticate(api: ultima_scraper_api.api_types):
        authed = await api.login(guest=True)
        return authed

    async def get_all_posts(authed: ultima_scraper_api.auth_types):
        user = await authed.get_user("onlyfans")
        if isinstance(user, ultima_scraper_api.user_types):
            return await user.get_posts()

    async def bulk_ip(authed: ultima_scraper_api.auth_types):
        url = "https://checkip.amazonaws.com"
        urls = [url] * 100
        responses = await authed.session_manager.bulk_requests(urls)
        for response in responses:
            if response:
                print(await response.read())

    async def rate_limit_enabler(authed: ultima_scraper_api.auth_types):
        # Set the URL and number of requests to send
        url = "https://onlyfans.com/api2/v2/init"
        urls = [url] * 10000
        responses = await authed.session_manager.bulk_json_requests(urls)
        has_errors = any("error" in item for item in responses)
        assert has_errors == False

    config = UltimaScraperAPIConfig()
    api = ultima_scraper_api.select_api("OnlyFans", config=config)
    authed = await authenticate(api)
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
