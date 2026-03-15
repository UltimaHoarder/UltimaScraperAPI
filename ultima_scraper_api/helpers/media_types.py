"""
Media type normalization for cross-site compatibility.

Provides a unified way to normalize site-specific media types (photo, stream, gif, etc.)
to standard types (image, video, audio, text) used throughout the application.
"""

from __future__ import annotations


class MediaTypes:
    """
    Normalizes site-specific media types to standard types.

    Standard types: image, video, audio, text

    Usage:
        media_types = MediaTypes()
        normalized = media_types.normalize("photo")  # Returns "image"
        raw_types = media_types.get_raw_types("video")  # Returns ["video", "stream", "application"]
    """

    def __init__(self) -> None:
        # Grouped definitions for readability
        self.gif = ["gif"]
        self.image = ["photo", "image"]
        self.video = ["video", "stream", "application"]
        self.audio = ["audio"]
        self.text = ["text"]

        # Build reverse lookup for O(1) normalization
        self._lookup: dict[str, str] = {}
        for attr_name in ("gif", "image", "video", "audio", "text"):
            raw_types = getattr(self, attr_name)
            for raw in raw_types:
                self._lookup[raw.lower()] = attr_name

    def normalize(self, value: str) -> str:
        """
        Normalize a site-specific media type to a standard type.

        Args:
            value: Raw media type from API (e.g., "photo", "stream", "gif")

        Returns:
            Standard type: "gif", "image", "video", "audio", or "text"
            Returns original value if no mapping found.
        """
        return self._lookup.get(value.lower(), value)

    def get_raw_types(self, standard_type: str) -> list[str]:
        """
        Get all raw types that map to a standard type (reverse lookup).

        Args:
            standard_type: One of "gif", "image", "video", "audio", "text"

        Returns:
            List of raw types that normalize to this standard type.
        """
        return getattr(self, standard_type, [])

    def is_valid_standard(self, value: str) -> bool:
        """Check if a value is a valid standard type."""
        return value.lower() in ("gif", "image", "video", "audio", "text")

    def get_standard_types(self) -> list[str]:
        """Get list of all standard types."""
        return ["gif", "image", "video", "audio", "text"]


# Singleton instance for convenience
media_types = MediaTypes()
