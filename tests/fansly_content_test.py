from types import SimpleNamespace

import pytest

from ultima_scraper_api.apis.fansly.classes.collection_model import CollectionModel
from ultima_scraper_api.apis.fansly.classes.message_model import MessageModel
from ultima_scraper_api.apis.fansly.classes.post_model import PostModel
from ultima_scraper_api.apis.fansly.classes.story_model import StoryModel


def media_variant(height, url, mimetype="video/mp4"):
    return {
        "height": height,
        "mimetype": mimetype,
        "locations": [{"location": url}] if url else [],
    }


@pytest.fixture(params=[PostModel, MessageModel, StoryModel, CollectionModel])
def content(request):
    content = object.__new__(request.param)
    settings = SimpleNamespace(media_quality=SimpleNamespace(video="720"))
    content.author = SimpleNamespace(
        get_api=lambda: SimpleNamespace(get_site_settings=lambda: settings)
    )
    return content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("quality", "source_url", "variants", "expected"),
    [
        ("source", "https://media.test/original", [], "https://media.test/original"),
        ("source", None, [1080, 720], "https://media.test/1080"),
        ("1080", None, [1080, 720], "https://media.test/1080"),
        ("900", None, [1080, 720], "https://media.test/720"),
        ("240", None, [1080, 720], "https://media.test/720"),
        ("source", None, [], None),
    ],
)
async def test_content_media_selection(
    content, quality, source_url, variants, expected
):
    media = media_variant(2160, source_url)
    media["variants"] = [
        media_variant(height, f"https://media.test/{height}") for height in variants
    ] + [media_variant(480, "https://media.test/thumbnail", "image/jpeg")]

    assert await content.link_picker(media, quality) == expected
    parsed = content.url_picker(media, quality)
    assert (parsed.geturl() if parsed is not None else None) == expected


def test_content_uses_configured_quality(content):
    media = media_variant(2160, "https://media.test/original")
    media["variants"] = [media_variant(720, "https://media.test/720")]

    assert content.url_picker(media).geturl() == "https://media.test/720"
