# examples.py
"""
Example usage for UltimaScraperAPI with OnlyFansAPI.
"""
import asyncio

from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig


async def onlyfans_example():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    async with api.login_context(guest=True) as authed:
        if authed and authed.is_authed():
            user = await authed.get_user("onlyfans")
            if user:
                print(
                    f"OnlyFans user: {getattr(user, 'username', None)} (ID: {getattr(user, 'id', None)})"
                )
                post = await user.get_post(1813239887)
                print(
                    f"Post ID: {post.id}, Title: {post.text}, Created At: {post.created_at}"
                )


if __name__ == "__main__":
    asyncio.run(onlyfans_example())
