import asyncio

import ultima_scraper_api


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
    posts = await get_post(authed)
    if posts:
        for post in posts:
            author = await post.get_author()
            print(f"User: {author.username}\nContent: {post.text}")
            break


asyncio.run(main())
