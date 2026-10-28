"""Map string site identifiers onto the archive's BigInteger keys.

OnlyFans and Fansly identify users and content with integers, and the archive
stores those directly as primary keys. LoyalFans (and DarkFans) use opaque
strings such as ``Gre3PwNWFFC7X4-2BBYcqlJzoBCMF8lxM7bfh0DMqRkhg``. Those sites
expose ``id`` as a stable 63-bit hash of the string and keep the string itself
as ``uid``; the archive stores the string in ``external_id`` so it can always
be sent back to the site.
"""

from __future__ import annotations

import hashlib

_POSITIVE_INT64_MASK = 0x7FFF_FFFF_FFFF_FFFF


def native_id_to_db_id(native_id: str) -> int:
    """Return the archive key for a string site identifier.

    The first 8 bytes of SHA-256, masked to a positive signed 64-bit integer.
    The result is deterministic, so every worker derives the same key without
    a database round trip.

    Raises:
        ValueError: If ``native_id`` is empty.
    """
    if not native_id:
        raise ValueError("A site identifier is required")
    digest = hashlib.sha256(native_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & _POSITIVE_INT64_MASK
