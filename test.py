import ultima_scraper_api
import asyncio


async def main():
    async def authenticate(api: ultima_scraper_api.api_types):
        auth = api.add_auth()
        return await auth.login(guest=True)

    async def get_post(authed: ultima_scraper_api.auth_types):
        user = await authed.get_user("onlyfans")
        if isinstance(user, ultima_scraper_api.user_types):
            posts = await user.get_posts()
            return posts

    api = ultima_scraper_api.select_api("OnlyFans")
    authed = await authenticate(api)
    _posts = await get_post(authed)


asyncio.run(main())
