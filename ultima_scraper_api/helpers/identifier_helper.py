"""Helper functions for extracting and validating user identifiers from various inputs.

This module handles:
- Extracting identifiers from URLs (OnlyFans, Fansly, LoyalFans)
- Cleaning and normalizing raw input (removing @, whitespace, etc.)
- Validating identifiers based on platform-specific rules
- Parsing multiple identifiers from comma/newline-separated input
"""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse


def extract_identifier_from_url(url: str, site: str = "onlyfans") -> str | None:
    """Extract username or ID from a profile URL.

    Supports:
    - OnlyFans: https://onlyfans.com/<username_or_id>
    - Fansly: https://fansly.com/<username>
    - LoyalFans: https://www.loyalfans.com/<username>

    Args:
        url: The profile URL to parse
        site: Platform name ("onlyfans", "fansly", "loyalfans")

    Returns:
        Extracted identifier (username or ID) if valid, None otherwise

    Examples:
        >>> extract_identifier_from_url("https://onlyfans.com/testuser")
        'testuser'
        >>> extract_identifier_from_url("https://onlyfans.com/1234567")
        '1234567'
        >>> extract_identifier_from_url("https://fansly.com/SomeUser")
        'SomeUser'
        >>> extract_identifier_from_url("https://www.loyalfans.com/myuser")
        'myuser'
    """
    site = site.lower()

    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        path = parsed.path.strip("/")

        # Remove "www." prefix
        hostname = hostname.replace("www.", "")

        # Check platform-specific domains
        valid_domains = {
            "onlyfans": ["onlyfans.com"],
            "fansly": ["fansly.com"],
            "loyalfans": ["loyalfans.com"],
        }

        platform_domains = valid_domains.get(site, [])
        if hostname not in platform_domains:
            # URL doesn't match expected platform
            return None

        # Extract identifier from path
        # Path format: /<identifier> or /<identifier>/...
        parts = [p for p in path.split("/") if p]
        if not parts:
            return None

        identifier = parts[0]

        # Validate identifier format
        if site == "onlyfans":
            # OnlyFans: allow alphanumeric usernames OR numeric-only IDs
            if re.match(r"^[a-zA-Z0-9_-]+$", identifier):
                return identifier
        elif site in ("fansly", "loyalfans"):
            # Fansly/LoyalFans: alphanumeric only, not purely numeric
            if re.match(r"^[a-zA-Z0-9_-]+$", identifier) and not identifier.isdigit():
                return identifier

        return None

    except Exception:
        return None


def extract_identifier(raw_input: str, site: str = "onlyfans") -> str | None:
    """Extract and validate a single identifier from raw input.

    Handles:
    - Removing whitespace and "@" prefix
    - Detecting and parsing URLs
    - Validating based on platform rules

    Platform rules:
    - OnlyFans: alphanumeric usernames AND numeric-only IDs allowed
    - Fansly: alphanumeric only, NOT purely numeric
    - LoyalFans: alphanumeric only, NOT purely numeric

    Args:
        raw_input: Raw input string (username, ID, or URL)
        site: Platform name ("onlyfans", "fansly", "loyalfans")

    Returns:
        Cleaned and validated identifier, or None if invalid

    Examples:
        >>> extract_identifier(" @testuser ", "onlyfans")
        'testuser'
        >>> extract_identifier("https://onlyfans.com/1234567", "onlyfans")
        '1234567'
        >>> extract_identifier("1234567", "onlyfans")
        '1234567'
        >>> extract_identifier("1234567", "fansly")
        None  # Purely numeric not allowed on Fansly
        >>> extract_identifier("https://fansly.com/SomeUser", "fansly")
        'SomeUser'
    """
    if not raw_input:
        return None

    site = site.lower()
    cleaned = raw_input.strip()

    # Check if input looks like a URL
    if any(
        domain in cleaned.lower()
        for domain in ["onlyfans.com", "fansly.com", "loyalfans.com"]
    ):
        return extract_identifier_from_url(cleaned, site)

    # Remove @ prefix
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]

    cleaned = cleaned.strip()

    if not cleaned:
        return None

    # Validate identifier based on platform rules
    if site == "onlyfans":
        # OnlyFans: allow alphanumeric usernames OR numeric-only IDs
        if re.match(r"^[a-zA-Z0-9_-]+$", cleaned):
            return cleaned
    elif site in ("fansly", "loyalfans"):
        # Fansly/LoyalFans: alphanumeric only, not purely numeric
        if re.match(r"^[a-zA-Z0-9_-]+$", cleaned) and not cleaned.isdigit():
            return cleaned

    return None


def parse_identifiers(input_text: str, site: str = "onlyfans") -> list[str]:
    """Parse multiple identifiers from comma/newline-separated input.

    Handles:
    - Splitting by newlines and commas
    - Cleaning and validating each entry
    - Removing duplicates while preserving order
    - Filtering out invalid identifiers

    Args:
        input_text: Raw input containing multiple identifiers
        site: Platform name ("onlyfans", "fansly", "loyalfans")

    Returns:
        List of unique, valid identifiers

    Example:
        >>> input_text = '''
        ...   @testuser, https://onlyfans.com/abc123
        ...   https://onlyfans.com/1234567
        ...   fansly.com/SomeUser
        ...   https://www.loyalfans.com/987654
        ... '''
        >>> parse_identifiers(input_text, "onlyfans")
        ['testuser', 'abc123', '1234567']
        >>> parse_identifiers(input_text, "fansly")
        ['testuser', 'abc123', 'SomeUser']  # '1234567' and '987654' filtered (numeric only)
        >>> parse_identifiers(input_text, "loyalfans")
        ['testuser', 'abc123', 'SomeUser']  # '1234567' and '987654' filtered (numeric only)
    """
    if not input_text:
        return []

    # Split by newlines and commas
    raw_entries: list[str] = []
    for line in input_text.split("\n"):
        # Further split by commas
        for entry in line.split(","):
            entry = entry.strip()
            if entry:
                raw_entries.append(entry)

    # Extract and validate each identifier
    identifiers: list[str] = []
    seen: set[str] = set()

    for raw_entry in raw_entries:
        identifier = extract_identifier(raw_entry, site)
        if identifier and identifier not in seen:
            identifiers.append(identifier)
            seen.add(identifier)

    return identifiers


def validate_identifier(identifier: str, site: str = "onlyfans") -> bool:
    """Validate an identifier according to platform rules.

    Args:
        identifier: The identifier to validate
        site: Platform name ("onlyfans", "fansly", "loyalfans")

    Returns:
        True if identifier is valid for the platform, False otherwise

    Examples:
        >>> validate_identifier("testuser", "onlyfans")
        True
        >>> validate_identifier("1234567", "onlyfans")
        True
        >>> validate_identifier("1234567", "fansly")
        False
        >>> validate_identifier("test_user-123", "onlyfans")
        True
    """
    if not identifier:
        return False

    site = site.lower()

    if site == "onlyfans":
        # OnlyFans: allow alphanumeric usernames OR numeric-only IDs
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", identifier))
    elif site in ("fansly", "loyalfans"):
        # Fansly/LoyalFans: alphanumeric only, not purely numeric
        return bool(
            re.match(r"^[a-zA-Z0-9_-]+$", identifier) and not identifier.isdigit()
        )

    return False


def resolve_site_name(site_name: str) -> str:
    site_name = site_name.lower()
    match site_name:
        case "onlyfans":
            return "OnlyFans"
        case "fansly":
            return "Fansly"
        case "loyalfans":
            return "LoyalFans"
        case _:
            raise ValueError(f"Invalid site name: {site_name}")
