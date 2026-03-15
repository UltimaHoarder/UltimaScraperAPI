"""Typed event models shared across UltimaScraper projects.

These Pydantic models define the canonical schema for events published on Redis
pub/sub channels (e.g. hooks channels consumed by the TUI).

This module intentionally lives in UltimaScraperAPI so that projects like
UltimaScraperTheReturn and workers can share a single source of truth.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

type JSONScalar = str | int | float | bool | None

type JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


class DownloadFailureReason(str, Enum):
    """Categorized reasons for download failures."""

    # Pre-download failures (detected before HTTP request)
    CONTENT_EXPIRED = "content_expired"  # Post expires_at passed, content deleted
    URL_EXPIRED = "url_expired"  # CDN URL signature expired (pre-check)
    NO_URL = "no_url"  # Media has no download URL at all
    IP_MISMATCH = "ip_mismatch"  # Download IP doesn't match signed URL IP

    # Runtime failures (detected during HTTP request)
    URL_EXPIRED_RUNTIME = "url_expired_runtime"  # HTTP 403/401/410
    CONTENT_DELETED_RUNTIME = "content_deleted_runtime"  # HTTP 404
    DOWNLOAD_ERROR = "download_error"  # Network error, timeout, 5xx

    # Post-download failures
    SIZE_MISMATCH = "size_mismatch"  # Downloaded size != expected

    # Success states (for completeness)
    ALREADY_EXISTS = "already_exists"  # File already on disk

    @property
    def is_recoverable(self) -> bool:
        """Whether this failure type can potentially be recovered via rescrape/retry."""
        return self in {
            DownloadFailureReason.URL_EXPIRED,
            DownloadFailureReason.NO_URL,
            DownloadFailureReason.URL_EXPIRED_RUNTIME,
            DownloadFailureReason.IP_MISMATCH,
            DownloadFailureReason.DOWNLOAD_ERROR,
            DownloadFailureReason.SIZE_MISMATCH,
        }

    @property
    def human_readable(self) -> str:
        """Human-readable description of the failure."""
        descriptions: dict[DownloadFailureReason, str] = {
            DownloadFailureReason.CONTENT_EXPIRED: "Content was scheduled for deletion and has expired",
            DownloadFailureReason.URL_EXPIRED: "Download URL has expired (needs rescrape)",
            DownloadFailureReason.NO_URL: "No download URL available (needs rescrape)",
            DownloadFailureReason.IP_MISMATCH: "CDN rejected request — download IP doesn't match URL's IP lock (use matching proxy)",
            DownloadFailureReason.URL_EXPIRED_RUNTIME: "Download URL was invalidated (needs rescrape)",
            DownloadFailureReason.CONTENT_DELETED_RUNTIME: "Content was deleted by creator",
            DownloadFailureReason.DOWNLOAD_ERROR: "Network or server error during download",
            DownloadFailureReason.SIZE_MISMATCH: "Downloaded file was corrupted (size mismatch)",
            DownloadFailureReason.ALREADY_EXISTS: "File already exists on disk",
        }
        return descriptions.get(self, self.value)


def create_download_progress_event(
    *,
    job_id: str,
    task_id: str,
    download_id: str,
    username: str,
    user_id: int,
    content_type: str,
    worker_id: str | None,
    dm_event: dict[str, Any],
    progress_state: dict[str, Any],
    progress_start: float,
    total_downloads: int,
) -> OperationProgressEvent:
    """Create a typed OperationProgressEvent from DownloadManager callback data.

    Args:
        job_id: Job identifier
        task_id: Task identifier
        download_id: Download session ID
        username: Creator username
        user_id: Creator user ID
        content_type: Content type (Posts, Messages, etc.)
        worker_id: Worker identifier
        dm_event: Event dict from DownloadManager callback
        progress_state: Mutable dict tracking download progress
        progress_start: Timestamp when download started (perf_counter)
        total_downloads: Total number of items to download

    Returns:
        Typed OperationProgressEvent ready for publishing
    """
    import time

    status = dm_event.get("status") or "completed"
    item_obj = dm_event.get("item")

    # Extract media_id from DownloadItem
    media_id_value: str | None = None
    if item_obj is not None and hasattr(item_obj, "media_id"):
        media_id = getattr(item_obj, "media_id", None)
        media_id_value = str(media_id) if media_id else None

    # Update progress counters
    bytes_delta = int(dm_event.get("bytes") or 0)
    if status == "completed":
        progress_state["total_bytes"] = int(progress_state["total_bytes"]) + max(
            bytes_delta, 0
        )

    completed_count = int(dm_event.get("completed", progress_state["completed"]))
    failed_count = int(dm_event.get("failed", progress_state["failed"]))
    progress_state["completed"] = completed_count
    progress_state["failed"] = failed_count

    # Calculate speeds
    now = time.perf_counter()
    elapsed = max(now - progress_start, 1e-6)
    last_time = float(progress_state["last_time"])
    delta = max(now - last_time, 1e-6)
    progress_state["last_time"] = now

    speed_bps = bytes_delta / delta if bytes_delta else 0.0
    total_bytes = int(progress_state["total_bytes"])
    avg_speed_bps = total_bytes / elapsed if total_bytes else 0.0

    return OperationProgressEvent(
        event="download_progress",
        job_id=job_id,
        task_id=task_id,
        download_id=download_id,
        username=username,
        user_id=user_id,
        content_type=content_type,
        worker_id=worker_id,
        media_type="mixed",
        status=status,  # type: ignore[arg-type]  # Literal validated by Pydantic
        media_id=media_id_value,
        path=dm_event.get("path"),
        bytes=bytes_delta,
        total_bytes=total_bytes,
        speed_bps=speed_bps,
        avg_speed_bps=avg_speed_bps,
        completed=completed_count,
        failed=failed_count,
        total=total_downloads,
    )


class DownloadError(BaseModel):
    """Individual error detail for a download failure."""

    reason: DownloadFailureReason
    message: str
    details: dict[str, str | int | None] | None = None

    @property
    def is_recoverable(self) -> bool:
        """Whether this specific error can be recovered."""
        return self.reason.is_recoverable

    @property
    def human_readable(self) -> str:
        """Human-readable description of the error."""
        return self.reason.human_readable


class DownloadResultItem(BaseModel):
    """Individual download result for a single media item."""

    media_id: int
    content_id: int | None = None
    status: Literal["downloaded", "skipped", "failed"]
    errors: list[DownloadError] = Field(default_factory=list)
    path: str | None = None
    url: str | None = None
    bytes_written: int = 0
    http_status: int | None = None
    content_expires_at: datetime | None = None
    url_expires_at: datetime | None = None

    def has_error(self, reason: DownloadFailureReason) -> bool:
        """Check if this result has a specific error reason."""
        return any(e.reason == reason for e in self.errors)

    @property
    def is_recoverable(self) -> bool:
        """Whether this failure can potentially be recovered."""
        if self.status != "failed":
            return False
        return any(e.is_recoverable for e in self.errors)

    def add_error(
        self,
        reason: DownloadFailureReason,
        message: str,
        details: dict[str, str | int | None] | None = None,
    ) -> None:
        """Add an error to this result."""
        self.errors.append(
            DownloadError(reason=reason, message=message, details=details)
        )


class BaseJobEvent(BaseModel):
    """Base class for all job system events."""

    event: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when event was created",
    )
    job_id: str = Field(description="Job identifier this event belongs to")
    task_id: str | None = Field(
        default=None, description="Task identifier (None for job-level events)"
    )

    class Config:
        frozen = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class TaskProgressEvent(BaseJobEvent):
    """Generic task execution progress event."""

    event: Literal["task_progress"] = "task_progress"
    progress: float = Field(ge=0.0, le=100.0, description="Progress percentage (0-100)")
    message: str | None = Field(default=None, description="Progress message")
    current: int | None = Field(default=None, description="Current item count")
    total: int | None = Field(default=None, description="Total item count")


class OperationProgressEvent(BaseJobEvent):
    """Unified operation progress event for downloads and scrapes."""

    event: Literal["download_progress", "scrape_progress"] = Field(
        description="Operation type: 'download_progress' or 'scrape_progress'"
    )

    # Common fields
    username: str = Field(description="Creator username")
    user_id: int = Field(description="Creator user ID")
    content_type: str = Field(
        description="Content type (Posts, Messages, Stories, etc.)"
    )
    status: Literal["started", "progress", "completed", "failed"] = Field(
        description="Current operation status"
    )
    worker_id: str | None = Field(
        default=None,
        description="Worker identifier that emitted this event (if applicable)",
    )

    # Download-specific
    download_id: str | None = Field(
        default=None, description="Unique download session ID"
    )
    media_type: str | None = Field(
        default=None, description="Media type: images, videos, audio"
    )
    media_id: str | None = Field(default=None, description="Media identifier")
    path: str | None = Field(
        default=None, description="File path for completed downloads"
    )
    bytes: int = Field(default=0, ge=0, description="Bytes transferred in this update")
    total_bytes: int = Field(default=0, ge=0, description="Total bytes transferred")
    speed_bps: float = Field(
        default=0.0, ge=0.0, description="Instantaneous speed (bytes/sec)"
    )
    avg_speed_bps: float = Field(
        default=0.0, ge=0.0, description="Average speed since start"
    )
    completed: int = Field(default=0, ge=0, description="Number of files completed")
    failed: int = Field(default=0, ge=0, description="Number of files failed")
    total: int = Field(default=0, ge=0, description="Total number of files")

    # Scrape-specific
    items_scraped: int = Field(default=0, ge=0, description="Number of items scraped")
    items_saved: int = Field(default=0, ge=0, description="Number of items saved")
    total_items: int | None = Field(
        default=None, description="Total items to scrape if known"
    )
    page: int | None = Field(default=None, description="Current page number")
    has_more: bool | None = Field(
        default=None, description="Whether more pages available"
    )

    @property
    def is_download(self) -> bool:
        return self.event == "download_progress"

    @property
    def is_scrape(self) -> bool:
        return self.event == "scrape_progress"

    @property
    def is_started(self) -> bool:
        return self.status == "started"

    @property
    def is_in_progress(self) -> bool:
        return self.status == "progress"

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"


class APICommandEvent(BaseJobEvent):
    """API Explorer command result event."""

    event: Literal["api_command_result"] = "api_command_result"
    command: str = Field(description="API command that was executed")
    success: bool = Field(description="Whether command succeeded")
    message: str | None = Field(default=None, description="Result message")
    output: dict[str, JSONValue] | None = Field(
        default=None, description="Command output data (JSON-serializable)"
    )
    execution_time: float | None = Field(
        default=None, ge=0.0, description="Command execution time in seconds"
    )


class TaskStatusEvent(BaseJobEvent):
    """Task execution status event (started/completed/failed)."""

    event: Literal["task_started", "task_completed", "task_failed"] = Field(
        description="Task status: 'task_started', 'task_completed', or 'task_failed'"
    )
    task_type: str = Field(description="Type of task (SCRAPE, DOWNLOAD, API_COMMAND)")
    worker_id: str | None = Field(
        default=None, description="Worker that executed the task"
    )

    execution_time: float | None = Field(
        default=None,
        ge=0.0,
        description="Task execution time in seconds (completed only)",
    )
    message: str | None = Field(
        default=None, description="Completion message or summary"
    )
    error: str | None = Field(default=None, description="Error message (failed only)")
    traceback: str | None = Field(
        default=None, description="Exception traceback (failed only)"
    )

    @property
    def is_started(self) -> bool:
        return self.event == "task_started"

    @property
    def is_completed(self) -> bool:
        return self.event == "task_completed"

    @property
    def is_failed(self) -> bool:
        return self.event == "task_failed"


class JobProgressEvent(BaseJobEvent):
    """Job progress event published to TUI.

    Handles all job lifecycle events:
    - job_dispatched: Job was dispatched to a backend
    - job_progress: Job progress update (task completed/failed)
    - job_completed: All job tasks finished
    - job_started: Job started executing
    - job_cancelled: Job was cancelled
    """

    event: Literal[
        "job_progress",
        "job_dispatched",
        "job_completed",
        "job_failed",
        "job_started",
        "job_cancelled",
    ] = "job_progress"
    job_name: str = Field(default="", description="Human-readable job name")
    status: str = Field(
        default="pending",
        description="Current job state (pending, running, completed, failed)",
    )
    total_tasks: int = Field(
        default=0, ge=0, description="Total number of tasks in job"
    )
    completed_tasks: int = Field(
        default=0, ge=0, description="Number of completed tasks"
    )
    failed_tasks: int = Field(default=0, ge=0, description="Number of failed tasks")
    # Optional fields for job_dispatched event
    backend_id: str | None = Field(
        default=None, description="Backend ID for job_dispatched"
    )
    priority: int = Field(default=0, description="Job priority")


class WorkerStatusEvent(BaseJobEvent):
    """Worker status change event (online/offline)."""

    event: Literal["worker_online", "worker_offline"] = Field(
        description="Worker status: 'worker_online' or 'worker_offline'"
    )
    worker_id: str = Field(description="Unique worker identifier")
    sites: list[str] = Field(default_factory=list, description="Supported sites")

    job_id: str = Field(
        default="system", description="Always 'system' for worker events"
    )
    task_id: str | None = Field(default=None)

    @property
    def is_online(self) -> bool:
        return self.event == "worker_online"

    @property
    def is_offline(self) -> bool:
        return self.event == "worker_offline"


class MediaStatusEvent(BaseJobEvent):
    """Media file save status event (saved/failed)."""

    event: Literal["media_saved", "media_failed"] = Field(
        description="Media status: 'media_saved' or 'media_failed'"
    )
    username: str = Field(description="Creator username")
    user_id: int = Field(description="Creator user ID")
    content_type: str = Field(description="Content type (Posts, Messages, Stories)")
    media_type: str = Field(description="Media category (images, videos, audio)")
    media_id: int | None = Field(default=None, description="Media identifier")
    count: int = Field(default=1, ge=1, description="Number of media items")

    job_id: str = Field(default="scrape", description="Job ID if available")
    task_id: str | None = Field(default=None)

    @property
    def is_saved(self) -> bool:
        return self.event == "media_saved"

    @property
    def is_failed(self) -> bool:
        return self.event == "media_failed"


class SubscriptionSyncCompleteEvent(BaseJobEvent):
    """Subscription sync completed."""

    event: Literal["subscription_sync_complete"] = "subscription_sync_complete"
    auth_id: str = Field(description="Authenticated user ID")
    username: str = Field(description="Authenticated username")
    total: int = Field(ge=0, description="Total subscriptions synced")
    inactive_count: int = Field(ge=0, description="Inactive subscriptions found")

    job_id: str = Field(default="sync", description="Job ID if available")
    task_id: str | None = Field(default=None)


class LogMessageEvent(BaseJobEvent):
    """Log message from a worker or other process."""

    event: Literal["log_message"] = "log_message"
    level: str = Field(description="Log level (INFO, WARNING, ERROR, DEBUG, CRITICAL)")
    level_no: int = Field(description="Numeric log level")
    logger: str = Field(description="Logger name")
    process: str = Field(description="Process name")
    message: str = Field(description="Log message")
    module: str = Field(description="Module name")
    function: str = Field(description="Function name")
    line: int = Field(description="Line number")
    exception: str | None = Field(
        default=None, description="Exception traceback if present"
    )

    job_id: str = Field(default="log", description="Job ID if available")
    task_id: str | None = Field(default=None)


class ReloadUserDataEvent(BaseJobEvent):
    """Reload user/subscription data from database."""

    event: Literal["reload_user_data"] = "reload_user_data"
    account_id: int = Field(description="Account ID to reload")
    username: str = Field(description="Username of the account")
    site: str = Field(description="Site name (e.g., onlyfans)")
    worker_id: str = Field(description="ID of the worker triggering the reload")
    from_job: str | None = Field(
        default=None, description="Job ID that triggered the reload"
    )

    job_id: str = Field(default="reload", description="Job ID if available")
    task_id: str | None = Field(default=None)


JobSystemEvent = (
    TaskProgressEvent
    | OperationProgressEvent
    | APICommandEvent
    | TaskStatusEvent
    | JobProgressEvent
    | WorkerStatusEvent
    | MediaStatusEvent
    | SubscriptionSyncCompleteEvent
    | LogMessageEvent
    | ReloadUserDataEvent
)


def publish_event(event: BaseJobEvent) -> dict[str, JSONValue]:
    """Convert an event to a JSON-serializable dict for publishing."""
    return event.model_dump(mode="json")


__all__ = [
    "APICommandEvent",
    "BaseJobEvent",
    "DownloadFailureReason",
    "DownloadResultItem",
    "JobProgressEvent",
    "JobSystemEvent",
    "JSONScalar",
    "JSONValue",
    "LogMessageEvent",
    "MediaStatusEvent",
    "OperationProgressEvent",
    "ReloadUserDataEvent",
    "SubscriptionSyncCompleteEvent",
    "TaskProgressEvent",
    "TaskStatusEvent",
    "WorkerStatusEvent",
    "create_download_progress_event",
    "publish_event",
]
