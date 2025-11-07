from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans.classes.only_drm import DRMMedia

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes import content_types


class MediaFileSource:
    """Represents a single file source with URL and dimensions."""

    def __init__(self, option: dict[str, Any]) -> None:
        self.url: str = option.get("url", "")
        self.width: int = option.get("width", 0)
        self.height: int = option.get("height", 0)
        self.size: int = option.get("size", 0)
        self.sources: list[Any] = option.get("sources", [])


class DRM:
    def __init__(self, option: dict[str, Any], media: MediaModel) -> None:
        self.dash: DRMManifest = DRMManifest(
            option["manifest"]["dash"], option["signature"]["dash"], media
        )
        self.hls: DRMManifest = DRMManifest(
            option["manifest"]["hls"], option["signature"]["hls"], media
        )
        self.__media__ = media

    def get_mpd_url(self) -> str:
        authed_drm = self.__media__.content.author.get_authed().drm
        assert authed_drm
        return self.dash.manifest_url

    async def resolve_drm(self) -> tuple[str, str, str]:
        authed_drm = self.__media__.content.author.get_authed().drm
        if not authed_drm:
            raise ValueError("Authed does not have DRM capabilities.")
        (
            video_url,
            audio_url,
            key,
        ) = await authed_drm.resolve_drm(self.dash.__drm_media__)
        return video_url, audio_url, key


class DRMManifest:
    """Model for DRM information of OnlyFans media."""

    def __init__(self, url: str, option: dict[str, Any], media: MediaModel) -> None:
        self.manifest_url: str = url
        self.key_pair_id: str = option["CloudFront-Key-Pair-Id"]
        self.policy: str = option["CloudFront-Policy"]
        self.signature: str = option["CloudFront-Signature"]
        response_type = getattr(media.content, "responseType", None)
        self.__drm_media__ = DRMMedia(
            media.id,
            self.manifest_url,
            self.key_pair_id,
            self.policy,
            self.signature,
            media.content.id,
            response_type,
        )
        self.__media__ = media


class MediaFiles:
    """Container for different media file versions (full, thumb, preview, etc.)."""

    def __init__(self, option: dict[str, Any], media: MediaModel) -> None:
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
        self.drm: DRM | None = DRM(option["drm"], media) if "drm" in option else None


class MediaModel:
    """Model for OnlyFans media items (photos, videos, etc.)."""

    def __init__(self, option: dict[str, Any], content: content_types) -> None:
        self.id: int = option["id"]
        self.content: content_types = content
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
        self.files: MediaFiles | None = (
            MediaFiles(files_data, self) if files_data else None
        )

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

    def has_drm(self) -> bool:
        return self.files is not None and self.files.drm is not None
