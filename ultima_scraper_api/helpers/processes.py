"""Owned subprocesses with bounded diagnostics and cancellation cleanup."""

from __future__ import annotations

import asyncio
import io
import os
import signal
import subprocess
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    stdout_truncated: bool
    stderr_truncated: bool


class OutputTail:
    def __init__(self, limit: int):
        self.limit = limit
        self.data = bytearray()
        self.truncated = False

    def feed(self, chunk: bytes) -> None:
        excess = len(self.data) + len(chunk) - self.limit
        if excess > 0:
            self.truncated = True
            del self.data[:excess]
        self.data.extend(chunk[-self.limit :])


async def finish_owned(task: asyncio.Future[Any]) -> Any:
    """Finish already-owned cleanup despite repeated caller cancellation."""
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
    return task.result()


async def run_blocking(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Keep a blocking file operation owned until its thread has stopped."""
    task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await finish_owned(task)
        except Exception:
            pass
        raise


def _validate_output_bytes(output_bytes: int) -> None:
    if (
        isinstance(output_bytes, bool)
        or not isinstance(output_bytes, int)
        or output_bytes <= 0
    ):
        raise ValueError("output_bytes must be a positive integer")


def _kill(process: asyncio.subprocess.Process) -> None:
    try:
        if os.name == "posix":
            # Every invocation owns a new session/process group, so cancellation
            # also stops descendants that could retain the output pipes.
            os.killpg(process.pid, signal.SIGKILL)
        elif process.returncode is None:
            process.kill()
    except ProcessLookupError:
        pass


async def run_process(
    args: Sequence[str],
    *,
    output_bytes: int = io.DEFAULT_BUFFER_SIZE,
    stdout_consumer: Callable[[bytes], None] | None = None,
) -> ProcessResult:
    """Drain both pipes; retain only their separately bounded diagnostic tails.

    The complete stdout stream can be inspected incrementally by a synchronous
    consumer. Commands and arguments are never included in diagnostics here.
    Cancellation kills and reaps the owned process before returning to callers.
    """
    _validate_output_bytes(output_bytes)
    spawn = asyncio.create_task(
        asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=output_bytes,
            start_new_session=os.name == "posix",
        )
    )
    try:
        process = await asyncio.shield(spawn)
    except asyncio.CancelledError:
        try:
            process = await finish_owned(spawn)
        except Exception:
            raise asyncio.CancelledError from None
        _kill(process)

        # Pipe transports must keep draining until process exit even if the
        # caller was cancelled while create_subprocess_exec was still pending.
        async def discard(stream):
            while await stream.read(io.DEFAULT_BUFFER_SIZE):
                pass

        await finish_owned(
            asyncio.gather(
                process.wait(),
                discard(process.stdout),
                discard(process.stderr),
                return_exceptions=True,
            )
        )
        raise

    stdout = OutputTail(output_bytes)
    stderr = OutputTail(output_bytes)

    async def drain(stream, tail, consumer=None):
        consumer_error = None
        while chunk := await stream.read(io.DEFAULT_BUFFER_SIZE):
            tail.feed(chunk)
            if consumer is not None:
                try:
                    consumer(chunk)
                except Exception as exc:
                    consumer_error = exc
                    consumer = None
                    _kill(process)
        if consumer_error is not None:
            raise consumer_error

    drains = [
        asyncio.create_task(drain(process.stdout, stdout, stdout_consumer)),
        asyncio.create_task(drain(process.stderr, stderr)),
    ]
    waiter = asyncio.create_task(process.wait())
    completion = asyncio.gather(waiter, *drains)
    try:
        # Observe drain failures while the process is running; a failed parser
        # must not leave a writer blocked behind an undrained pipe.
        await asyncio.shield(completion)
    except BaseException:
        _kill(process)
        await finish_owned(asyncio.gather(waiter, *drains, return_exceptions=True))
        # Retrieve any parser exception from the shielded group as well.
        if completion.done() and not completion.cancelled():
            completion.exception()
        raise
    return ProcessResult(
        process.returncode,
        bytes(stdout.data),
        bytes(stderr.data),
        stdout.truncated,
        stderr.truncated,
    )


def run_process_sync(
    args: Sequence[str],
    *,
    output_bytes: int = io.DEFAULT_BUFFER_SIZE,
    stdout_consumer: Callable[[bytes], None] | None = None,
) -> ProcessResult:
    """Synchronous compatibility entry point with the same output bounds."""
    _validate_output_bytes(output_bytes)
    stdout, stderr = OutputTail(output_bytes), OutputTail(output_bytes)
    errors = []
    with subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=os.name == "posix",
    ) as process:

        def kill():
            try:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                elif process.poll() is None:
                    process.kill()
            except ProcessLookupError:
                pass

        def drain(stream, tail, consumer=None):
            try:
                while chunk := stream.read(io.DEFAULT_BUFFER_SIZE):
                    tail.feed(chunk)
                    if consumer is not None:
                        consumer(chunk)
            except Exception as exc:
                errors.append(exc)
                kill()

        threads = [
            threading.Thread(
                target=drain, args=(process.stdout, stdout, stdout_consumer)
            ),
            threading.Thread(target=drain, args=(process.stderr, stderr)),
        ]
        for thread in threads:
            thread.start()
        try:
            process.wait()
        finally:
            if process.poll() is None:
                kill()
            process.wait()
            for thread in threads:
                thread.join()
    if errors:
        raise errors[0]
    return ProcessResult(
        process.returncode,
        bytes(stdout.data),
        bytes(stderr.data),
        stdout.truncated,
        stderr.truncated,
    )
