"""
OnlyFans DRM Resolution and Media Formatting Module

This module provides functionality for:
1. DRM content resolution and decryption using Widevine
2. Async media merging workflow using ffmpeg
3. Bounded subprocess output and owned cancellation cleanup

Compatible with Python 3.14+
"""

import asyncio
import logging
import io
import os
import platform
import re
import shutil
from concurrent.futures import Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import ffmpeg  # type: ignore
import orjson
import xmltodict
from aiohttp import ClientConnectionError, ClientPayloadError

from ultima_scraper_core.environment import runtime_env_value
from ultima_scraper_core.processes import ProcessResult, finish_owned, run_blocking, run_process, run_process_sync
from ultima_scraper_api.apis.onlyfans.urls import APIRoutes

if TYPE_CHECKING:
    import ultima_scraper_api

    auth_types = ultima_scraper_api.auth_types

# Configure logging
logger = logging.getLogger(__name__)
os_name = platform.system()

# API Endpoint Notes:
# Replace authed with your ClientSession
# Replace APIRoutes().drm_resolver with "https://onlyfans.com/api2/v2/users/media/{MEDIA_ID}/drm/{RESPONSE_TYPE}/{CONTENT_ID}?type=widevine"
# If the content is from mass messages, omit the response_type and content_id, the end result will look like "https://onlyfans.com/api2/v2/users/media/{MEDIA_ID}/drm/?type=widevine"


def _resource_limit(name: str, value: int | None, fallback: int) -> int:
    raw = value if value is not None else runtime_env_value(name)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return fallback
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        raise ValueError(f"{name} must be a positive integer")
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


@dataclass
class _MergeRequest:
    output_filepath: Path
    media_paths: list[Path]
    future: Future[bool] = field(default_factory=Future)
    settled: asyncio.Event = field(default_factory=asyncio.Event)
    operation: asyncio.Task[bool] | None = None


class MediaFormatter:
    """Bounded media merge admission and owned asynchronous subprocesses."""

    def __init__(
        self,
        max_workers: int | None = None,
        *,
        queue_entries: int | None = None,
        output_bytes: int | None = None,
    ) -> None:
        self.max_workers = _resource_limit(
            "ULTIMA_MEDIA_PROCESS_CONCURRENCY", max_workers, 5
        )
        self.queue_entries = _resource_limit(
            "ULTIMA_MEDIA_PROCESS_QUEUE_ENTRIES", queue_entries, self.max_workers
        )
        self.output_bytes = _resource_limit(
            "ULTIMA_MEDIA_PROCESS_OUTPUT_BYTES", output_bytes, io.DEFAULT_BUFFER_SIZE
        )
        self.merge_queue: asyncio.Queue[_MergeRequest] = asyncio.Queue(
            self.queue_entries
        )
        self.workers: list[asyncio.Task[None]] = []
        self._process_slots = asyncio.Semaphore(self.max_workers)
        self._closing = False
        self._closed = False
        self._process_tasks: set[asyncio.Task[ProcessResult]] = set()

    async def run_process(self, args: list[str], *, stdout_consumer=None):
        if self._closed:
            raise RuntimeError("Media formatter is closed")

        async def admitted():
            async with self._process_slots:
                return await run_process(
                    args,
                    output_bytes=self.output_bytes,
                    stdout_consumer=stdout_consumer,
                )

        task = asyncio.create_task(admitted())
        self._process_tasks.add(task)
        try:
            return await task
        finally:
            self._process_tasks.discard(task)

    @staticmethod
    def _probe_args(filepath: Path) -> list[str]:
        return [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=format_name",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            filepath.as_posix(),
        ]

    @staticmethod
    def _preferred_format(filepath: Path, result: ProcessResult) -> str:
        if result.returncode:
            error = result.stderr.decode(errors="replace")
            if "moov atom not found" in error or "Invalid data found" in error:
                extension = filepath.suffix.lower().lstrip(".")
                return (
                    extension
                    if extension in {"mp4", "mov", "avi", "mkv", "webm", "flv"}
                    else "mp4"
                )
            raise RuntimeError(f"Error probing file {filepath}: {error}")
        if result.stdout_truncated:
            raise RuntimeError(
                "Media format response exceeds configured diagnostic buffer"
            )
        formats = result.stdout.decode(errors="strict").strip().split(",")
        if not formats[0]:
            raise RuntimeError(f"No media format returned for {filepath}")
        return "mp4" if "mp4" in formats else formats[0]

    def get_preferred_format(self, filepath: Path) -> str:
        """Synchronous compatibility method; async paths use the owned runner."""
        return self._preferred_format(
            filepath,
            run_process_sync(
                self._probe_args(filepath), output_bytes=self.output_bytes
            ),
        )

    async def format_media(
        self, output_filepath: Path, media_paths: list[Path]
    ) -> bool:
        if not media_paths:
            return True
        temporary = output_filepath.with_suffix(".part")
        try:
            if len(media_paths) == 1:
                async with self._process_slots:
                    await run_blocking(shutil.copy, media_paths[0], temporary)
            else:
                video, audio = media_paths[:2]
                output_format = self._preferred_format(
                    video, await self.run_process(self._probe_args(video))
                )
                command = ffmpeg.output(
                    ffmpeg.input(video.as_posix()),
                    ffmpeg.input(audio.as_posix()),
                    temporary.as_posix(),
                    vcodec="copy",
                    acodec="copy",
                    f=output_format,
                ).compile(overwrite_output=True)
                result = await self.run_process(command)
                if result.returncode:
                    logger.error(
                        "FFmpeg error merging %s: %s",
                        output_filepath.name,
                        result.stderr.decode(errors="replace"),
                    )
                    return False
            temporary.replace(output_filepath)
            return True
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Error merging %s: %s", output_filepath.name, exc)
            return False
        finally:
            # run_process/run_blocking finish their owned work before this runs.
            temporary.unlink(missing_ok=True)

    async def ffmpeg_worker(self) -> None:
        while True:
            try:
                request = await self.merge_queue.get()
            except asyncio.QueueShutDown:
                return
            try:
                if request.future.cancelled():
                    continue
                request.operation = asyncio.create_task(
                    self.format_media(request.output_filepath, request.media_paths)
                )
                loop = asyncio.get_running_loop()
                operation = request.operation

                def cancel_operation(future, *, operation=operation, loop=loop):
                    if future.cancelled() and not operation.done():
                        try:
                            loop.call_soon_threadsafe(operation.cancel)
                        except RuntimeError:
                            pass

                request.future.add_done_callback(cancel_operation)
                try:
                    result = await request.operation
                except asyncio.CancelledError:
                    request.future.cancel()
                    current = asyncio.current_task()
                    if current is not None and current.cancelling():
                        raise
                    continue
                except Exception as exc:
                    if not request.future.done():
                        request.future.set_exception(exc)
                    continue
                if not request.future.done():
                    request.future.set_result(result)
                    # Failed/cancelled merges preserve their source streams.
                    if result:
                        for path in request.media_paths:
                            if path != request.output_filepath:
                                try:
                                    path.unlink(missing_ok=True)
                                except OSError as exc:
                                    logger.warning(
                                        "Merged file is ready, but source cleanup failed for %s: %s",
                                        path,
                                        exc,
                                    )
            finally:
                request.settled.set()
                self.merge_queue.task_done()

    def _request(self, output_filepath: Path, media_paths: list[Path]) -> _MergeRequest:
        if self._closing:
            raise RuntimeError("Media formatter is shutting down")
        return _MergeRequest(output_filepath, media_paths)

    def add_task(self, output_filepath: Path, media_paths: list[Path]) -> Future[bool]:
        """Nonblocking compatibility entry point; QueueFull reports backpressure."""
        request = self._request(output_filepath, media_paths)
        self.merge_queue.put_nowait(request)
        return request.future

    async def merge(self, output_filepath: Path, media_paths: list[Path]) -> bool:
        """Wait for queue capacity and keep cancellation cleanup owned."""
        request = self._request(output_filepath, media_paths)
        if not self.workers:
            raise RuntimeError("Start media formatter workers before awaiting a merge")
        await self.merge_queue.put(request)
        try:
            return await asyncio.wrap_future(request.future)
        except asyncio.CancelledError:
            request.future.cancel()
            if request.operation is not None:
                await finish_owned(asyncio.create_task(request.settled.wait()))
            raise

    def start_workers(self, n: int = 1) -> None:
        if self._closing:
            raise RuntimeError("Media formatter is shutting down")
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError("n must be a positive integer")
        self.workers.extend(
            asyncio.create_task(self.ffmpeg_worker(), name="ffmpeg_worker")
            for _ in range(n)
        )

    def _cancel_queued(self):
        while True:
            try:
                request = self.merge_queue.get_nowait()
            except (asyncio.QueueEmpty, asyncio.QueueShutDown):
                return
            request.future.cancel()
            request.settled.set()
            self.merge_queue.task_done()

    async def shutdown(self) -> None:
        self._closing = True
        self.merge_queue.shutdown()
        if not self.workers:
            self._cancel_queued()
        try:
            await self.merge_queue.join()
            await asyncio.gather(*self.workers)
            self._closed = True
            # Include directly awaited probes/decryption as well as merges.
            await asyncio.gather(*self._process_tasks, return_exceptions=True)
        except asyncio.CancelledError:
            self._closed = True
            self._cancel_queued()
            owned = [*self.workers, *self._process_tasks]
            for task in owned:
                task.cancel()
            await finish_owned(asyncio.gather(*owned, return_exceptions=True))
            raise
        finally:
            self._closed = True
            self.workers.clear()

class DRMMedia:
    def __init__(
        self,
        media_id: int,
        manifest_url: str,
        key_pair_id: str,
        policy: str,
        signature: str,
        content_id: int,
        video_url: str | None = None,
        audio_url: str | None = None,
        video_size: int | None = None,
        audio_size: int | None = None,
        content_type: str | None = None,
    ) -> None:
        self.media_id = media_id

        self.manifest_url = manifest_url
        self.key_pair_id = key_pair_id
        self.policy = policy
        self.signature = signature
        self.video_url = video_url
        self.audio_url = audio_url
        self.video_size = video_size
        self.audio_size = audio_size

        self.content_id = content_id
        self.content_type = content_type
        self.os_name = os_name

    def extract_directory_from_url(self, manifest_url: str):
        path = urlparse(manifest_url).path
        match = re.search(r"files/(.*?)/\w+\.mpd$", path)
        assert match
        directory = match.group(1)
        return directory

    def get_cookies(self):
        cookie_str = (
            f"CloudFront-Key-Pair-Id={self.key_pair_id}; "
            f"CloudFront-Policy={self.policy}; "
            f"CloudFront-Signature={self.signature};"
        ).strip()
        return cookie_str

    async def get_pssh(self, mpd: dict[str, Any]) -> str | None:
        tracks = mpd["MPD"]["Period"]["AdaptationSet"]
        if isinstance(tracks, dict):
            tracks = [tracks]
        for video_tracks in tracks:
            mime_type = video_tracks.get("@mimeType", "")
            if mime_type.startswith("video/") or mime_type.startswith("audio/"):
                content_protection = video_tracks.get("ContentProtection", [])
                if isinstance(content_protection, dict):
                    content_protection = [content_protection]
                for t in content_protection:
                    if (
                        t.get("@schemeIdUri", "").lower()
                        == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"
                    ):
                        return t.get("cenc:pssh")
        return None

    def get_video_url(self, mpd: dict[str, Any]):
        directory_url = self.extract_directory_from_url(self.manifest_url)
        adaptation_sets = mpd["MPD"]["Period"]["AdaptationSet"]
        if isinstance(adaptation_sets, dict):
            if adaptation_sets.get("@mimeType", "").startswith("video/"):
                adaptation_set = adaptation_sets
            else:
                return None
        else:
            adaptation_set = next(
                (
                    s
                    for s in adaptation_sets
                    if s.get("@mimeType", "").startswith("video/")
                ),
                None,
            )

        if not adaptation_set:
            return None

        representation: list[dict[str, Any]] | dict[str, Any] = adaptation_set[
            "Representation"
        ]
        if isinstance(representation, list):
            base_url = representation[0]["BaseURL"]
        else:
            base_url = representation["BaseURL"]
        if isinstance(base_url, dict):
            base_url = base_url.get("#text", "")
        media_url = APIRoutes().cdn_resolver(
            directory_url, base_url, drm=True, manifest_type=self.get_manifest_type()
        )
        return media_url

    def get_audio_url(self, mpd: dict[str, Any]):
        directory_url = self.extract_directory_from_url(self.manifest_url)
        adaptation_sets = mpd["MPD"]["Period"]["AdaptationSet"]
        if isinstance(adaptation_sets, dict):
            if adaptation_sets.get("@mimeType", "").startswith("audio/"):
                adaptation_set = adaptation_sets
            else:
                return None
        else:
            adaptation_set = next(
                (
                    s
                    for s in adaptation_sets
                    if s.get("@mimeType", "").startswith("audio/")
                ),
                None,
            )

        if not adaptation_set:
            return None

        representation: list[dict[str, Any]] | dict[str, Any] = adaptation_set[
            "Representation"
        ]
        if isinstance(representation, list):
            base_url: str = representation[0]["BaseURL"]
        else:
            base_url: str = representation["BaseURL"]
        if isinstance(base_url, dict):
            base_url = base_url.get("#text", "")
        media_url = APIRoutes().cdn_resolver(
            directory_url, base_url, drm=True, manifest_type=self.get_manifest_type()
        )
        return media_url

    def resolve_filename(self) -> str | None:
        url = self.video_url or self.audio_url
        return os.path.basename(urlparse(url).path) if url else None

    def get_manifest_type(self) -> str:
        for part in urlparse(self.manifest_url).path.split("/"):
            if part == "dash" or part.endswith("_dash"):
                return part
        raise ValueError(
            f"Could not determine manifest type from URL: {self.manifest_url}"
        )


class OnlyDRM:
    """
    Handles DRM resolution and decrypted media workflow.

    This class manages:
    - Widevine DRM resolution and license acquisition
    - Content decryption using mp4decrypt
    - Integration with MediaFormatter for async media merging

    Attributes:
        device: Widevine device for DRM operations
        cdm: Content Decryption Module instance
        session_id: Active CDM session ID
        authed: Authenticated API client
        media_formatter: Reference to MediaFormatter for merge queue operations
    """

    def __init__(
        self,
        client_key_path: Path,
        private_key_path: Path,
        authed: "auth_types",
        mp4decrypt_path: Path | None = None,
        mp4dump_path: Path | None = None,
        media_formatter: MediaFormatter | None = None,
        auto_start_workers: bool = True,
        max_workers: int | None = None,
    ) -> None:
        """
        Initialize OnlyDRM with Widevine credentials and media formatter.

        Args:
            client_key_path: Path to Widevine client key file
            private_key_path: Path to Widevine private key file
            authed: Authenticated API client for making requests
            mp4decrypt_path: Optional path to mp4decrypt binary (auto-detected if None)
            mp4dump_path: Optional path to mp4dump binary (auto-detected if None)
            media_formatter: MediaFormatter instance (creates new one if None)
            auto_start_workers: Whether to automatically start workers (default: True)
            max_workers: Maximum concurrent media subprocesses per formatter
        """
        # Load Widevine credentials
        self.client_key = client_key_path.read_bytes()
        self.private_key = private_key_path.read_bytes()

        # Find or use provided Bento4 tools
        self.mp4decrypt_filepath = (
            self._find_bento4_tool("mp4decrypt")
            if mp4decrypt_path is None
            else mp4decrypt_path
        )
        self.mp4dump_filepath = (
            self._find_bento4_tool("mp4dump") if mp4dump_path is None else mp4dump_path
        )

        # Validate required tools exist
        if self.mp4decrypt_filepath is None:
            raise FileNotFoundError(
                "mp4decrypt not found in PATH. Please install Bento4 tools: "
                "https://www.bento4.com/downloads/"
            )
        if self.mp4dump_filepath is None:
            raise FileNotFoundError(
                "mp4dump not found in PATH. Please install Bento4 tools: "
                "https://www.bento4.com/downloads/"
            )

        # Initialize Widevine device and CDM
        # Plain media models/formatters also import this module. Load the
        # license machinery only when an authenticated DRM session needs it.
        from pywidevine import Device, DeviceTypes
        from pywidevine.cdm import Cdm

        self.device = Device(
            type_=DeviceTypes.ANDROID,
            security_level=3,
            flags={},
            client_id=self.client_key,
            private_key=self.private_key,
        )
        self.cdm = Cdm.from_device(self.device)  # type: ignore
        self.session_id = self.cdm.open()

        # Store references
        self.os_name = os_name
        self.authed = authed

        # Initialize or use provided MediaFormatter
        self.media_formatter = media_formatter or MediaFormatter(
            max_workers=max_workers
        )

        # Auto-start workers if requested
        if auto_start_workers and not self.media_formatter.workers:
            worker_count = self.media_formatter.max_workers
            self.media_formatter.start_workers(worker_count)
            logger.info(f"Auto-started {worker_count} MediaFormatter workers")

        logger.info("OnlyDRM initialized with CDM session")

    def _find_bento4_tool(self, tool_name: str) -> Path | None:
        """
        Find a Bento4 tool in the system PATH.

        Args:
            tool_name: Name of the tool (e.g., 'mp4decrypt', 'mp4dump')

        Returns:
            Path to the tool if found, None otherwise
        """
        # Add .exe extension on Windows
        if platform.system() == "Windows":
            tool_name = f"{tool_name}.exe"

        # Search in PATH
        tool_path = shutil.which(tool_name)
        return Path(tool_path) if tool_path else None

    def extract_hex_id(self, dash_url: str) -> str:
        """
        Extract hexadecimal media ID from DASH URL.

        Args:
            dash_url: DASH manifest URL containing hex ID

        Returns:
            Extracted hex ID string

        Raises:
            AssertionError: If hex ID pattern not found in URL
        """
        match = re.search(r"/([0-9a-f]{32})/", dash_url)
        assert match, f"Could not extract hex ID from URL: {dash_url}"
        hex_id = match.group(1)
        return hex_id

    async def _read_drm_response(self, url: str, **kwargs: Any) -> bytes:
        """Read while the response is owned; retry interrupted body transfers."""
        requester = self.authed.get_requester()
        attempts = max(1, int(requester.get_session_manager().max_attempts or 1))
        for attempt in range(attempts):
            # Request establishment already has its own retry policy.
            response = await requester.request(url, **kwargs)
            if response is None:
                raise RuntimeError("DRM request returned no response")
            try:
                response.raise_for_status()
                return await response.read()
            except (ClientConnectionError, ClientPayloadError, TimeoutError) as exc:
                if attempt + 1 >= attempts:
                    raise
                logger.warning(
                    "DRM response read interrupted (%s), attempt %d/%d",
                    type(exc).__name__, attempt + 1, attempts,
                )
            finally:
                response.release()
            await asyncio.sleep(min(2 ** attempt, 30))
        raise RuntimeError("DRM response attempts exhausted")

    async def get_manifest(self, drm_media: "DRMMedia") -> dict[str, Any]:
        """
        Fetch and parse MPD manifest from CDN with CloudFront authentication.

        Args:
            drm_media: DRMMedia object containing manifest URL and CloudFront credentials

        Returns:
            Parsed manifest as dictionary

        Raises:
            AssertionError: If request fails
        """
        manifest_url = drm_media.manifest_url

        # Build CloudFront cookie string for authentication
        cookie_str = (
            f"CloudFront-Key-Pair-Id={drm_media.key_pair_id}; "
            f"CloudFront-Policy={drm_media.policy}; "
            f"CloudFront-Signature={drm_media.signature};"
        ).strip()

        # Fetch manifest from CDN
        body = await self._read_drm_response(
            manifest_url, premade_settings="", custom_cookies=cookie_str
        )

        # Parse XML manifest to dictionary
        xml = xmltodict.parse(body)
        manifest: dict[str, Any] = orjson.loads(orjson.dumps(xml))

        logger.debug(f"Successfully fetched manifest for media {drm_media.media_id}")
        return manifest

    async def get_license(self, drm_media: "DRMMedia", raw_pssh: str) -> bytes:
        """
        Acquire Widevine license from OnlyFans license server.

        Args:
            drm_media: DRMMedia object with license server details
            raw_pssh: Base64-encoded PSSH (Protection System Specific Header)

        Returns:
            License response bytes from server

        Raises:
            AssertionError: If license request fails
        """
        # Parse PSSH and generate license challenge
        from pywidevine.pssh import PSSH

        pssh = PSSH(raw_pssh)
        challenge = self.cdm.get_license_challenge(self.session_id, pssh)

        # Build license server URL
        url = APIRoutes().drm_resolver(
            drm_media.media_id, drm_media.content_type, drm_media.content_id
        )

        # Request license from server
        licence = await self._read_drm_response(
            url, method="POST", data=challenge
        )

        logger.debug(f"Successfully acquired license for media {drm_media.media_id}")
        return licence

    async def get_keys(self, licence: bytes) -> list[Any]:
        """
        Parse license and extract decryption keys.

        Args:
            licence: License response bytes from server

        Returns:
            List of decryption keys with KID and key data
        """
        session_id = self.session_id
        cdm = self.cdm

        # Parse license and extract keys
        cdm.parse_license(session_id, licence)
        keys = cdm.get_keys(session_id)

        logger.debug(f"Extracted {len(keys)} decryption keys from license")
        return keys

    async def resolve_drm(
        self, drm_media: "DRMMedia"
    ) -> tuple[str | None, str | None, str]:
        """
        Complete DRM resolution workflow: fetch manifest, acquire license, extract keys.

        Args:
            drm_media: DRMMedia object with all necessary DRM information

        Returns:
            Tuple of (video_url, audio_url, decryption_key)
        """
        logger.info(f"Starting DRM resolution for media {drm_media.media_id}")

        # Step 1: Fetch and parse manifest
        manifest = await self.get_manifest(drm_media)

        # Step 2: Extract PSSH from manifest
        pssh = await drm_media.get_pssh(manifest)
        assert pssh, "Could not extract PSSH from manifest"

        # Step 3: Acquire license
        license = await self.get_license(drm_media, pssh)

        # Step 4: Extract decryption keys
        keys = await self.get_keys(license)
        content_key = keys[-1]  # Last key is typically the content key
        key = f"{content_key.kid.hex}:{content_key.key.hex()}"  # type: ignore

        # Step 5: Extract media URLs from manifest
        drm_media.video_url = drm_media.get_video_url(manifest)
        drm_media.audio_url = drm_media.get_audio_url(manifest)

        logger.info(f"DRM resolution complete for media {drm_media.media_id}")
        return drm_media.video_url, drm_media.audio_url, key

    @staticmethod
    def _decryption_paths(filepath: Path, directory: Path | None):
        output = filepath.with_name(filepath.name.replace(".enc", ".dec"))
        if directory is not None:
            output = directory / output.name
        return output, output.with_suffix(".part" + output.suffix)

    @staticmethod
    def _encryption_probe():
        # Retain only enough overlap to recognize a marker spanning pipe reads.
        state = {"encrypted": False, "overlap": b""}

        def consume(chunk):
            if not state["encrypted"]:
                chunk = state["overlap"] + chunk
                state["encrypted"] = b"encv" in chunk or b"enca" in chunk
                state["overlap"] = chunk[-3:]

        return state, consume

    def _is_file_encrypted(self, filepath: Path) -> bool:
        state, consume = self._encryption_probe()
        result = run_process_sync(
            [str(self.mp4dump_filepath), str(filepath)],
            output_bytes=self.media_formatter.output_bytes,
            stdout_consumer=consume,
        )
        if result.returncode:
            raise RuntimeError(
                f"mp4dump failed: {result.stderr.decode(errors='replace')}"
            )
        return state["encrypted"]

    async def _is_file_encrypted_async(self, filepath: Path) -> bool:
        state, consume = self._encryption_probe()
        result = await self.media_formatter.run_process(
            [str(self.mp4dump_filepath), str(filepath)],
            stdout_consumer=consume,
        )
        if result.returncode:
            raise RuntimeError(
                f"mp4dump failed: {result.stderr.decode(errors='replace')}"
            )
        return state["encrypted"]

    @staticmethod
    def _commit_decryption(filepath: Path, temporary: Path, output: Path) -> Path:
        # Publish successfully before removing the retryable encrypted input.
        temporary.replace(output)
        if filepath != output:
            filepath.unlink()
        return output

    def decrypt_file(
        self, filepath: Path, key: str, temp_output_path: Path | None = None
    ) -> Path:
        """Synchronous compatibility entry point with bounded diagnostics."""
        output, temporary = self._decryption_paths(filepath, temp_output_path)
        if not self._is_file_encrypted(filepath):
            return output if output.exists() else filepath
        try:
            result = run_process_sync(
                [
                    str(self.mp4decrypt_filepath),
                    str(filepath),
                    str(temporary),
                    "--key",
                    key,
                ],
                output_bytes=self.media_formatter.output_bytes,
            )
            if result.returncode:
                raise RuntimeError(
                    f"mp4decrypt failed: {result.stderr.decode(errors='replace')}"
                )
            return self._commit_decryption(filepath, temporary, output)
        finally:
            temporary.unlink(missing_ok=True)

    async def decrypt_file_async(
        self, filepath: Path, key: str, temp_output_path: Path | None = None
    ) -> Path:
        """Decrypt with bounded output and reap the process on cancellation."""
        output, temporary = self._decryption_paths(filepath, temp_output_path)
        if not await self._is_file_encrypted_async(filepath):
            return output if output.exists() else filepath
        try:
            result = await self.media_formatter.run_process(
                [
                    str(self.mp4decrypt_filepath),
                    str(filepath),
                    str(temporary),
                    "--key",
                    key,
                ],
            )
            if result.returncode:
                raise RuntimeError(
                    f"mp4decrypt failed: {result.stderr.decode(errors='replace')}"
                )
            return self._commit_decryption(filepath, temporary, output)
        finally:
            temporary.unlink(missing_ok=True)

    async def merge_media(self, output_filepath: Path, media_paths: list[Path]) -> bool:
        return await self.media_formatter.merge(output_filepath, media_paths)

    def enqueue_merge_task(
        self, output_filepath: Path, media_paths: list[Path]
    ) -> Future[bool]:
        """
        Enqueue a media merge task to the MediaFormatter queue.

        Args:
            output_filepath: Desired path for merged output file
            media_paths: List of media files to merge (typically video + audio)

        Returns:
            Future that will resolve to merge success status
        """
        logger.info(
            f"Enqueueing merge task for {len(media_paths)} files -> {output_filepath.name}"
        )
        return self.media_formatter.add_task(output_filepath, media_paths)

    async def shutdown(self) -> None:
        """
        Gracefully shutdown OnlyDRM and cleanup resources.

        This method:
        - Closes the Widevine CDM session
        - Shuts down the MediaFormatter queue and workers
        """
        logger.info("Shutting down OnlyDRM...")

        # Close CDM session
        if self.session_id:
            self.cdm.close(self.session_id)
            logger.debug("Closed CDM session")

        # Shutdown MediaFormatter
        await self.media_formatter.shutdown()

        logger.info("OnlyDRM shutdown complete")

    async def __aenter__(self) -> "OnlyDRM":
        """Context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Context manager exit with automatic cleanup."""
        await self.shutdown()
