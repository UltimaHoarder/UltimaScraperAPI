from __future__ import annotations

from typing import Any


class MediaFileSource:
    """Represents a single file source with URL and dimensions."""

    def __init__(self, option: dict[str, Any]) -> None:
        self.url: str = option.get("url", "")
        self.width: int = option.get("width", 0)
        self.height: int = option.get("height", 0)
        self.size: int = option.get("size", 0)
        self.sources: list[Any] = option.get("sources", [])


class MediaFiles:
    """Container for different media file versions (full, thumb, preview, etc.)."""

    def __init__(self, option: dict[str, Any]) -> None:
        full_opt: dict[str, Any] | None = option.get("full")
        thumb_opt: dict[str, Any] | None = option.get("thumb")
        preview_opt: dict[str, Any] | None = option.get("preview")
        square_opt: dict[str, Any] | None = option.get("squarePreview")

        self.full: MediaFileSource | None = (
            MediaFileSource(full_opt) if isinstance(full_opt, dict) else None
        )
        self.thumb: MediaFileSource | None = (
            MediaFileSource(thumb_opt) if isinstance(thumb_opt, dict) else None
        )
        self.preview: MediaFileSource | None = (
            MediaFileSource(preview_opt) if isinstance(preview_opt, dict) else None
        )
        self.squarePreview: MediaFileSource | None = (
            MediaFileSource(square_opt) if isinstance(square_opt, dict) else None
        )


class MediaModel:
    """Model for OnlyFans media items (photos, videos, etc.)."""

    def __init__(self, option: dict[str, Any]) -> None:
        self.id: int = option["id"]
        self.type: str = option["type"]
        self.convertedToVideo: bool = option.get("convertedToVideo", False)
        self.canView: bool = option.get("canView", False)
        self.hasError: bool = option.get("hasError", False)
        self.createdAt: str | None = option.get("createdAt")
        self.isReady: bool = option.get("isReady", False)
        self.duration: int = option.get("duration", 0)
        self.hasCustomPreview: bool = option.get("hasCustomPreview", False)

        # Parse nested files structure
        files_data = option.get("files", {})
        self.files: MediaFiles | None = MediaFiles(files_data) if files_data else None

        # Handle legacy "source" format (for backward compatibility)
        if "source" in option and not self.files:
            # Legacy format uses "source" dict directly
            self.source: dict[str, Any] = option["source"]
        else:
            self.source: dict[str, Any] = {}

        # Video quality sources
        self.videoSources: dict[str, str | None] = option.get("videoSources", {})

        # Store raw dict for backward compatibility
        self.__raw__ = option

    def to_dict(self) -> dict[str, Any]:
        """Convert back to dict format for backward compatibility."""
        return self.__raw__

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access for backward compatibility."""
        return self.__raw__[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Allow dict-like .get() for backward compatibility."""
        return self.__raw__.get(key, default)
