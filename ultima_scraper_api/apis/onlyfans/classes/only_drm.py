"""
OnlyFans DRM Resolution and Media Formatting Module

This module provides functionality for:
1. DRM content resolution and decryption using Widevine
2. Async media merging workflow using ffmpeg
3. Thread-based execution of blocking ffmpeg operations

Compatible with Python 3.14+
"""

import asyncio
import logging
import platform
import re
import shutil
import subprocess
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ffmpeg  # type: ignore
import orjson
import xmltodict
from pywidevine import Device, DeviceTypes
from pywidevine.cdm import Cdm
from pywidevine.pssh import PSSH

from ultima_scraper_api.apis.onlyfans.classes.extras import endpoint_links

if TYPE_CHECKING:
    import ultima_scraper_api

    auth_types = ultima_scraper_api.auth_types

# Configure logging
logger = logging.getLogger(__name__)
os_name = platform.system()

# API Endpoint Notes:
# Replace authed with your ClientSession
# Replace endpoint_links.drm_resolver with "https://onlyfans.com/api2/v2/users/media/{MEDIA_ID}/drm/{RESPONSE_TYPE}/{CONTENT_ID}?type=widevine"
# If the content is from mass messages, omit the response_type and content_id, the end result will look like "https://onlyfans.com/api2/v2/users/media/{MEDIA_ID}/drm/?type=widevine"


class MediaFormatter:
    """
    Handles async media merging using ffmpeg-python.

    This class manages:
    - Async queue for media merge tasks
    - ThreadPoolExecutor for blocking ffmpeg calls
    - Format detection and media merging workflow
    - Worker threads that consume and process merge tasks

    Attributes:
        merge_queue: Asyncio queue holding pending merge tasks
        executor: ThreadPoolExecutor for running blocking ffmpeg operations
        workers: List of active worker coroutines
    """

    def __init__(self, max_workers: int = 5) -> None:
        """
        Initialize MediaFormatter with async queue and thread pool.

        Args:
            max_workers: Maximum number of threads for ffmpeg operations
        """
        # Initialize async queue for merge tasks
        # Each task is a tuple: (output_filepath, media_paths, result_future)
        self.merge_queue: asyncio.Queue[tuple[Path, list[Path], Future[bool]]] = (
            asyncio.Queue()
        )

        # ThreadPoolExecutor for blocking ffmpeg calls
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="ffmpeg_worker"
        )

        # Track active worker coroutines
        self.workers: list[asyncio.Task[None]] = []

        logger.info(f"MediaFormatter initialized with {max_workers} worker threads")

    def get_preferred_format(self, filepath: Path) -> str:
        """
        Extract the preferred container format from the file.

        Prioritizes 'mp4' if available in format list, otherwise uses first format.

        Args:
            filepath: Path to media file

        Returns:
            Preferred format name (e.g., 'mp4', 'mov')

        Raises:
            Exception: If ffprobe fails with unexpected error
        """
        try:
            # Use ffmpeg-python to probe file formats
            probe = ffmpeg.probe(filepath.as_posix())  # type: ignore
            format_names = probe["format"][
                "format_name"
            ]  # E.g., "mov,mp4,m4a,3gp,3g2,mj2"
            formats = format_names.split(",")  # Split into a list

            # Prioritize 'mp4' if available, otherwise take the first format
            preferred = "mp4" if "mp4" in formats else formats[0]
            logger.debug(f"Preferred format for {filepath.name}: {preferred}")
            return preferred
        except Exception as e:
            error_msg = str(e)

            # Handle corrupted files gracefully
            if "moov atom not found" in error_msg or "Invalid data found" in error_msg:
                # File is corrupted, try to infer from extension
                extension = filepath.suffix.lower().lstrip(".")
                if extension in ["mp4", "mov", "m4v", "avi", "mkv", "webm", "flv"]:
                    inferred_format = extension if extension != "m4v" else "mp4"
                    logger.warning(
                        f"File {filepath.name} is corrupted, inferred format: {inferred_format}"
                    )
                    return inferred_format
                # Default fallback for video files
                logger.warning(f"File {filepath.name} is corrupted, defaulting to mp4")
                return "mp4"
            else:
                # For other ffmpeg errors, re-raise
                logger.error(f"Error probing file {filepath}: {error_msg}")
                raise Exception(f"Error probing file {filepath}: {error_msg}")

    async def format_media(
        self, output_filepath: Path, media_paths: list[Path]
    ) -> bool:
        """
        Merge video and audio files using ffmpeg with codec copying.

        This method handles:
        - Multiple input files (typically video + audio from DASH)
        - Codec copying (no re-encoding) for fast merging
        - Temporary file handling to prevent corruption
        - Error handling and cleanup

        Args:
            output_filepath: Desired path for merged output file
            media_paths: List of media files to merge (video, audio, etc.)

        Returns:
            True if merge successful, False otherwise
        """
        # Skip merge if only one file (nothing to merge)
        if len(media_paths) <= 1:
            logger.info(
                f"Single file provided, no merge needed: {media_paths[0].name if media_paths else 'none'}"
            )
            return True

        try:
            # Extract video and audio paths
            dec_video_path, dec_audio_path = media_paths[0], media_paths[1]
            logger.info(
                f"Merging {dec_video_path.name} + {dec_audio_path.name} -> {output_filepath.name}"
            )

            # Create ffmpeg input streams
            video_input = ffmpeg.input(dec_video_path.as_posix())  # type: ignore
            audio_input = ffmpeg.input(dec_audio_path.as_posix())  # type: ignore

            # Dynamically determine the preferred output format
            output_format = self.get_preferred_format(dec_video_path)

            # Use temporary file during merge to prevent corruption
            temp_output_filepath = output_filepath.with_suffix(".part")

            # Run ffmpeg merge in thread pool (blocking operation)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: ffmpeg.output(  # type: ignore
                    video_input,  # type: ignore
                    audio_input,  # type: ignore
                    temp_output_filepath.as_posix(),
                    vcodec="copy",  # Copy video codec (no re-encoding)
                    acodec="copy",  # Copy audio codec (no re-encoding)
                    f=output_format,  # Dynamically set the format
                ).run(capture_stdout=True, capture_stderr=True, overwrite_output=True),
            )

            # Rename temp file to final output
            temp_output_filepath.rename(output_filepath)
            logger.info(f"Successfully merged media: {output_filepath.name}")
            return True

        except ffmpeg.Error as e:
            # Log ffmpeg errors with stderr output
            stderr = e.stderr.decode() if e.stderr else "No error details"  # type: ignore
            logger.error(f"FFmpeg error merging {output_filepath.name}: {stderr}")
            return False
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error merging {output_filepath.name}: {str(e)}")
            return False

    async def ffmpeg_worker(self) -> None:
        """
        Worker coroutine that consumes merge tasks from the queue.

        This worker:
        - Continuously polls the merge queue
        - Processes each merge task using format_media()
        - Sets the result future when complete
        - Cleans up temporary decrypted files after merge
        - Handles exceptions and sets future exceptions
        """
        logger.info("FFmpeg worker started")

        while True:
            try:
                # Wait for next task from queue
                output_filepath, media_paths, future = await self.merge_queue.get()
                logger.debug(f"Worker picked up merge task: {output_filepath.name}")

                try:
                    # Perform the media merge
                    result = await self.format_media(output_filepath, media_paths)

                    # Set the future result
                    future.set_result(result)

                    # Clean up decrypted temporary files
                    for path in media_paths:
                        if path.exists():
                            path.unlink()
                            logger.debug(f"Cleaned up temporary file: {path.name}")

                    logger.info(f"Worker completed merge task: {output_filepath.name}")

                except Exception as e:
                    # Set exception on future if merge fails
                    logger.error(
                        f"Worker error processing {output_filepath.name}: {str(e)}"
                    )
                    future.set_exception(e)

            except Exception as worker_error:
                # Log worker-level errors but continue processing
                logger.error(f"Worker encountered error: {str(worker_error)}")
                continue
            finally:
                # Mark task as done
                self.merge_queue.task_done()

    def add_task(self, output_filepath: Path, media_paths: list[Path]) -> Future[bool]:
        """
        Add a media merge task to the queue.

        This method:
        - Creates a Future for tracking task completion
        - Enqueues the task for worker processing
        - Returns the Future for async result tracking

        Args:
            output_filepath: Desired path for merged output file
            media_paths: List of media files to merge

        Returns:
            Future that will resolve to merge success status
        """
        # Create a Future to track task completion
        result_future: Future[bool] = Future()

        # Enqueue task (non-blocking)
        self.merge_queue.put_nowait((output_filepath, media_paths, result_future))

        logger.debug(
            f"Added merge task to queue: {output_filepath.name} (queue size: {self.merge_queue.qsize()})"
        )
        return result_future

    def start_workers(self, n: int = 1) -> None:
        """
        Start n worker coroutines to process merge tasks.

        Workers run concurrently and consume tasks from the merge queue.
        Each worker processes tasks until explicitly stopped.

        Args:
            n: Number of worker coroutines to start (default: 1)
        """
        logger.info(f"Starting {n} ffmpeg worker(s)")

        for i in range(n):
            # Create and schedule worker task
            worker_task = asyncio.create_task(
                self.ffmpeg_worker(), name=f"ffmpeg_worker_{i}"
            )
            self.workers.append(worker_task)
            logger.debug(f"Started worker {i+1}/{n}")

        logger.info(f"All {n} workers started and ready")

    async def shutdown(self) -> None:
        """
        Gracefully shutdown workers and cleanup resources.

        This method:
        - Waits for queue to be fully processed
        - Cancels all worker tasks
        - Shuts down the thread pool executor
        """
        logger.info("Shutting down MediaFormatter...")

        # Wait for all queued tasks to complete
        await self.merge_queue.join()
        logger.info("All merge tasks completed")

        # Cancel all worker tasks
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish cancellation
        await asyncio.gather(*self.workers, return_exceptions=True)
        logger.info("All workers stopped")

        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        logger.info("MediaFormatter shutdown complete")


class DRMMedia:
    def __init__(
        self,
        media_id: int,
        manifest_url: str,
        key_pair_id: str,
        policy: str,
        signature: str,
        content_id: int,
        content_type: str | None,
    ) -> None:
        self.media_id = media_id

        self.manifest_url = manifest_url
        self.key_pair_id = key_pair_id
        self.policy = policy
        self.signature = signature

        self.content_id = content_id
        self.content_type = content_type
        self.os_name = os_name

    def extract_directory_from_url(self, manifest_url: str):
        match = re.search(r"files/(.*?)/\w+\.mpd$", manifest_url)
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
        pssh_str = ""
        for video_tracks in tracks:
            if video_tracks["@mimeType"] == "video/mp4":
                for t in video_tracks["ContentProtection"]:
                    if (
                        t["@schemeIdUri"].lower()
                        == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"
                    ):
                        pssh_str = t["cenc:pssh"]
                        return pssh_str

    def get_video_url(self, mpd: dict[str, Any]):
        directory_url = self.extract_directory_from_url(self.manifest_url)
        adaptation_set = mpd["MPD"]["Period"]["AdaptationSet"][0]
        representation: list[dict[str, Any]] | dict[str, Any] = adaptation_set[
            "Representation"
        ]
        if isinstance(representation, list):
            base_url = representation[0]["BaseURL"]
        else:
            base_url = representation["BaseURL"]
        media_url = endpoint_links().cdn_resolver(directory_url, base_url, drm=True)
        return media_url

    def get_audio_url(self, mpd: dict[str, Any]):
        directory_url = self.extract_directory_from_url(self.manifest_url)
        adaptation_set = mpd["MPD"]["Period"]["AdaptationSet"][1]
        representation: list[dict[str, Any]] | dict[str, Any] = adaptation_set[
            "Representation"
        ]
        if isinstance(representation, list):
            base_url: str = representation[0]["BaseURL"]
        else:
            base_url: str = representation["BaseURL"]
        media_url = endpoint_links().cdn_resolver(directory_url, base_url, drm=True)
        return media_url


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
        max_workers: int = 5,
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
            max_workers: Maximum number of worker threads for MediaFormatter
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
            worker_count = self.media_formatter.executor._max_workers
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
        r = await self.authed.get_requester().request(
            manifest_url, premade_settings="", custom_cookies=cookie_str
        )
        assert r, f"Failed to fetch manifest from {manifest_url}"

        # Parse XML manifest to dictionary
        resp_text = await r.text()
        xml = xmltodict.parse(resp_text)
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
        pssh = PSSH(raw_pssh)
        challenge = self.cdm.get_license_challenge(self.session_id, pssh)

        # Build license server URL
        url = endpoint_links().drm_resolver(
            drm_media.media_id, drm_media.content_type, drm_media.content_id
        )

        # Request license from server
        licence = await self.authed.get_requester().request(
            url, method="POST", data=challenge
        )
        assert licence, f"Failed to acquire license from {url}"

        logger.debug(f"Successfully acquired license for media {drm_media.media_id}")
        return await licence.read()

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

    async def resolve_drm(self, drm_media: "DRMMedia") -> tuple[str, str, str]:
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
        video_url = drm_media.get_video_url(manifest)
        audio_url = drm_media.get_audio_url(manifest)

        logger.info(f"DRM resolution complete for media {drm_media.media_id}")
        return video_url, audio_url, key

    def decrypt_file(
        self, filepath: Path, key: str, temp_output_path: Path | None = None
    ) -> Path:
        """
        Decrypt a DRM-protected media file using mp4decrypt.

        Args:
            filepath: Path to encrypted file
            key: Decryption key in format "KID:KEY" (hex)
            temp_output_path: Optional directory for decrypted output

        Returns:
            Path to decrypted file

        Raises:
            FileNotFoundError: If mp4decrypt tool not found
            RuntimeError: If decryption fails
        """
        # Determine output path (replace .enc with .dec)
        output_filepath = Path(filepath.as_posix().replace(".enc", ".dec"))
        if temp_output_path:
            output_filepath = temp_output_path.joinpath(output_filepath.name)

        # Check if file is encrypted using mp4dump
        is_encrypted = self._is_file_encrypted(filepath)

        # Early return if already decrypted
        if output_filepath.exists() and not is_encrypted:
            logger.debug(f"Decrypted file already exists: {output_filepath}")
            return output_filepath

        # Skip decryption if file is not encrypted
        if not is_encrypted:
            logger.debug(f"File is not encrypted, returning as-is: {filepath.name}")
            return filepath

        # Use temporary file during decryption
        temp_output_filepath = output_filepath.with_suffix(
            ".part" + output_filepath.suffix
        )

        # Execute mp4decrypt subprocess
        logger.info(f"Decrypting {filepath.name} with key {key[:16]}...")
        result = subprocess.run(
            [
                str(self.mp4decrypt_filepath),
                str(filepath),
                str(temp_output_filepath),
                "--key",
                key,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Check for errors
        if result.returncode != 0:
            error_msg = result.stderr or "Unknown error"
            logger.error(f"Decryption failed: {error_msg}")
            # Clean up partial file
            if temp_output_filepath.exists():
                temp_output_filepath.unlink()
            raise RuntimeError(f"mp4decrypt failed: {error_msg}")

        # Success: remove encrypted file and rename temp file
        filepath.unlink()
        temp_output_filepath.rename(output_filepath)
        logger.info(f"Successfully decrypted: {output_filepath}")
        return output_filepath

    def _is_file_encrypted(self, filepath: Path) -> bool:
        """
        Check if a media file is encrypted using mp4dump.

        Args:
            filepath: Path to media file to check

        Returns:
            True if file contains encrypted tracks (encv/enca), False otherwise
        """
        result = subprocess.run(
            [str(self.mp4dump_filepath), str(filepath)],
            capture_output=True,
            text=True,
        )
        # Check for encrypted video (encv) or audio (enca) tracks
        return "encv" in result.stdout or "enca" in result.stdout

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
        - Shuts down the MediaFormatter workers and thread pool
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
