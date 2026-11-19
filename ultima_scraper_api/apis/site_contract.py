"""What the backend reads from a site API, written down in one place.

The backend never imports a site's classes to scrape it. It looks methods up by
name and reads fields off content and media by name (UltimaScraperBackend:
``job_system/handlers/scrape/content.py`` picks the methods,
``database/write_executor.py`` serializes the content). A site supports a
content type exactly when it has the method; a missing method skips it.

``capabilities()`` reports which of those methods a site's classes have,
``signature_problems()`` checks they accept the arguments the backend passes,
and ``content_problems()`` checks one content object the way the serializer
reads it. Keep these tables in step with the backend.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from urllib.parse import ParseResult

# Capability -> the methods the backend tries, preferred first.
AUTH_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "me": ("get_me",),
    "user_lookup": ("get_user",),
    "subscriptions": ("get_subscriptions",),
    "paid_content": ("iter_paid_content", "get_paid_content"),
    "chats": ("iter_chats", "get_chats"),
    "transactions": ("get_transactions",),
    "lists": ("get_lists",),
}
USER_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "posts": ("iter_posts", "get_posts"),
    "messages": ("iter_messages", "get_messages"),
    "stories": ("iter_stories", "get_stories"),
    "highlights": ("iter_highlight_stories", "get_highlights"),
    "post_by_id": ("get_post",),
    "message_by_id": ("get_message_by_id",),
    "socials": ("get_socials",),
}
REQUIRED_AUTH = ("me", "user_lookup", "subscriptions")
REQUIRED_USER = ("posts",)

# Keyword arguments the backend passes to each method, when the site has it.
# ``get_*`` fallbacks go through a signature filter in the backend, so only
# the streaming ``iter_*`` methods (called directly) and lookups are listed.
CALL_KWARGS: dict[str, tuple[str, ...]] = {
    "iter_posts": ("limit", "on_progress", "job_id"),
    "iter_messages": ("max_items", "on_progress", "job_id"),
    "iter_stories": ("max_items", "on_progress", "job_id"),
    "iter_highlight_stories": ("max_items", "on_progress", "job_id"),
    "iter_paid_content": ("performer_id", "limit", "cache"),
    "iter_chats": ("query", "limit"),
    "get_user": ("refresh",),
    "get_lists": ("refresh", "limit", "offset"),
}


def capabilities(
    target: object, table: Mapping[str, tuple[str, ...]]
) -> dict[str, str]:
    """Capability -> the method the backend would call on ``target``."""
    found: dict[str, str] = {}
    for capability, names in table.items():
        for name in names:
            if callable(getattr(target, name, None)):
                found[capability] = name
                break
    return found


def missing_required(target: object, *, auth: bool) -> list[str]:
    table, required = (
        (AUTH_CAPABILITIES, REQUIRED_AUTH) if auth else (USER_CAPABILITIES, REQUIRED_USER)
    )
    present = capabilities(target, table)
    return [name for name in required if name not in present]


def _accepts(function: Any, keyword: str) -> bool:
    parameters = inspect.signature(function).parameters.values()
    return any(
        p.kind is inspect.Parameter.VAR_KEYWORD
        or (p.name == keyword and p.kind is not inspect.Parameter.POSITIONAL_ONLY)
        for p in parameters
    )


def signature_problems(target: object) -> list[str]:
    """Methods present on ``target`` that would reject the backend's arguments."""
    problems: list[str] = []
    for name, keywords in CALL_KWARGS.items():
        method = getattr(target, name, None)
        if not callable(method):
            continue
        if name.startswith("iter_") and not inspect.isasyncgenfunction(method):
            problems.append(f"{name} is not an async generator")
        for keyword in keywords:
            if not _accepts(method, keyword):
                problems.append(f"{name} does not accept {keyword}=")
    return problems


def _read_field(value: object, *names: str) -> Any:
    # Same lookup order as the backend's write_executor._read_field.
    if isinstance(value, Mapping):
        for name in names:
            if value.get(name) is not None:
                return value[name]
        return None
    for name in names:
        candidate = getattr(value, name, None)
        if candidate is not None:
            return candidate
    raw = getattr(value, "__raw__", None)
    if isinstance(raw, Mapping):
        for name in names:
            if raw.get(name) is not None:
                return raw[name]
    return None


def _media_list(item: object) -> list[Any]:
    media = _read_field(item, "media")
    if isinstance(media, (str, bytes)) or not isinstance(media, Sequence):
        return []
    return list(media)


def content_problems(item: object) -> list[str]:
    """Why the backend could not store ``item``, or which fields it would lose."""
    problems: list[str] = []
    if _read_field(item, "id") is None:
        problems.append("no id")
    created = _read_field(item, "created_at", "createdAt", "postedAt")
    if created is None:
        problems.append("no created_at")
    elif not isinstance(created, (datetime, int, float, str)):
        problems.append(f"created_at is a {type(created).__name__}")
    if _read_field(item, "text", "rawText", "raw_text") is None:
        problems.append("no text")
    get_author = getattr(item, "get_author", None)
    if not callable(get_author):
        problems.append("no get_author()")
    elif _read_field(get_author(), "id") is None:
        problems.append("get_author() has no id")
    media = _media_list(item)
    picker = getattr(item, "url_picker", None)
    if media and not callable(picker):
        problems.append("media but no url_picker()")
    for index, entry in enumerate(media):
        if _read_field(entry, "id") is None:
            problems.append(f"media[{index}] has no id")
        if _read_field(entry, "type", "category") is None:
            problems.append(f"media[{index}] has no type")
        if callable(picker):
            parsed = picker(entry)
            if parsed is not None and not isinstance(parsed, ParseResult):
                problems.append(f"url_picker(media[{index}]) is not a ParseResult")
    return problems
