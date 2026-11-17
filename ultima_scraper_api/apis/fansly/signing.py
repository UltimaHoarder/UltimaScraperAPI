"""Request signing used by the Fansly web client.

Every API request the web app makes carries:

    fansly-client-id     the device id from GET /device/id
    fansly-client-ts     the client clock in milliseconds
    fansly-client-check  cyrb53("<key>_<url path>_<device id>") in hex

The server accepts requests without these headers, but a wrong
fansly-client-check is answered with 429, so either sign correctly or not at
all. The key and hash are read from the web app's main.js (the auth interceptor
assigns ``checkKey_`` twice; the second value is the live one).
"""

from __future__ import annotations

import time
from urllib.parse import urlsplit

CHECK_KEY = "necvac-govry3-tybkYz"

_MASK = 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    return (a * b) & _MASK


def cyrb53(text: str, seed: int = 0) -> int:
    """53-bit hash matching the web client's ``cyrb53`` (JS ``Math.imul`` arithmetic)."""
    h1 = (3735928559 ^ seed) & _MASK
    h2 = (1103547991 ^ seed) & _MASK
    for char in text:
        code = ord(char)
        h1 = _imul(h1 ^ code, 2654435761)
        h2 = _imul(h2 ^ code, 1597334677)
    h1 = _imul(h1 ^ (h1 >> 16), 2246822507)
    h1 ^= _imul(h2 ^ (h2 >> 13), 3266489909)
    h2 = _imul(h2 ^ (h2 >> 16), 2246822507)
    h2 ^= _imul(h1 ^ (h1 >> 13), 3266489909)
    return 4294967296 * (2097151 & h2) + h1


def client_check(url: str, device_id: str) -> str:
    """The fansly-client-check value for ``url`` (only its path is hashed)."""
    path = urlsplit(url).path
    return format(cyrb53(f"{CHECK_KEY}_{path}_{device_id}"), "x")


def signed_headers(url: str, device_id: str, now_ms: int | None = None) -> dict[str, str]:
    if not device_id:
        return {}
    timestamp = now_ms if now_ms is not None else int(time.time() * 1000)
    return {
        "fansly-client-id": device_id,
        "fansly-client-ts": str(timestamp),
        "fansly-client-check": client_check(url, device_id),
    }
