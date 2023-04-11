import asyncio

import ultima_scraper_api


async def main():
    async def authenticate(api: ultima_scraper_api.api_types):
        auth = api.add_auth()
        return await auth.login(guest=True)

    async def get_all_posts(authed: ultima_scraper_api.auth_types):
        user = await authed.get_user("onlyfans")
        if isinstance(user, ultima_scraper_api.user_types):
            return await user.get_posts()

    async def rate_limit_enabler(authed: ultima_scraper_api.auth_types):
        # Set the URL and number of requests to send
        url = "https://onlyfans.com/api2/v2/init"
        urls = [url] * 10000
        response = await authed.session_manager.bulk_json_requests(urls)
        are_all_dicts = all(isinstance(item, dict) for item in response)
        assert are_all_dicts == True

    api = ultima_scraper_api.select_api("OnlyFans")
    authed = await authenticate(api)

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
