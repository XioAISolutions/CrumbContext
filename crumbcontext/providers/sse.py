from __future__ import annotations

import asyncio
import json
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, AsyncIterable, AsyncIterator, Mapping, Protocol


@dataclass(frozen=True)
class SSEMessage:
    event: str
    data: str
    event_id: str | None = None
    retry_ms: int | None = None

    def json(self) -> dict[str, Any]:
        value = json.loads(self.data)
        if not isinstance(value, dict):
            raise ValueError("SSE data must decode to a JSON object")
        return value


class AsyncSSESource(Protocol):
    def __call__(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        timeout_seconds: float,
    ) -> AsyncIterator[bytes]: ...


class HTTPStreamError(RuntimeError):
    def __init__(self, status: int | None, body: str):
        self.status = status
        self.body = body
        label = f"HTTP {status}" if status is not None else "stream transport error"
        super().__init__(f"{label}: {body[:500]}")


async def decode_sse(chunks: AsyncIterable[bytes | str]) -> AsyncIterator[SSEMessage]:
    """Decode fragmented Server-Sent Events from an async byte/text source."""

    buffer = ""
    event = "message"
    data_lines: list[str] = []
    event_id: str | None = None
    retry_ms: int | None = None

    def dispatch() -> SSEMessage | None:
        nonlocal event, data_lines, event_id, retry_ms
        if not data_lines:
            event = "message"
            event_id = None
            retry_ms = None
            return None
        message = SSEMessage(
            event=event or "message",
            data="\n".join(data_lines),
            event_id=event_id,
            retry_ms=retry_ms,
        )
        event = "message"
        data_lines = []
        event_id = None
        retry_ms = None
        return message

    async for chunk in chunks:
        if isinstance(chunk, bytes):
            piece = chunk.decode("utf-8", errors="replace")
        elif isinstance(chunk, str):
            piece = chunk
        else:
            raise TypeError(f"SSE chunk must be bytes or str, got {type(chunk).__name__}")
        buffer += piece.replace("\r\n", "\n").replace("\r", "\n")
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if line == "":
                message = dispatch()
                if message is not None:
                    yield message
                continue
            if line.startswith(":"):
                continue
            field, separator, raw_value = line.partition(":")
            value = raw_value[1:] if separator and raw_value.startswith(" ") else raw_value
            if field == "event":
                event = value
            elif field == "data":
                data_lines.append(value)
            elif field == "id":
                event_id = value
            elif field == "retry":
                try:
                    retry_ms = int(value)
                except ValueError:
                    retry_ms = None

    if buffer:
        line = buffer
        if not line.startswith(":"):
            field, separator, raw_value = line.partition(":")
            value = raw_value[1:] if separator and raw_value.startswith(" ") else raw_value
            if field == "event":
                event = value
            elif field == "data":
                data_lines.append(value)
            elif field == "id":
                event_id = value
            elif field == "retry":
                try:
                    retry_ms = int(value)
                except ValueError:
                    retry_ms = None
    message = dispatch()
    if message is not None:
        yield message


async def urllib_sse_source(
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    timeout_seconds: float,
) -> AsyncIterator[bytes]:
    """Read an SSE response without adding a mandatory async HTTP dependency.

    Blocking urllib I/O runs in a daemon thread. Cancellation closes the shared
    response object when possible and always stops delivering further chunks.
    """

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
    stop = threading.Event()
    holder: dict[str, Any] = {}

    def emit(kind: str, value: Any = None) -> None:
        if loop.is_closed():
            return
        loop.call_soon_threadsafe(queue.put_nowait, (kind, value))

    def worker() -> None:
        request = urllib.request.Request(
            url=url,
            data=body,
            headers=dict(headers),
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request, timeout=timeout_seconds)
            holder["response"] = response
            status = getattr(response, "status", 200)
            if status >= 400:
                payload = response.read().decode("utf-8", errors="replace")
                emit("error", HTTPStreamError(status, payload))
                return
            while not stop.is_set():
                chunk = response.readline()
                if not chunk:
                    break
                emit("chunk", chunk)
        except urllib.error.HTTPError as exc:
            try:
                payload = exc.read().decode("utf-8", errors="replace")
            except Exception:
                payload = str(exc)
            emit("error", HTTPStreamError(exc.code, payload))
        except Exception as exc:
            emit("error", HTTPStreamError(None, str(exc)))
        finally:
            response = holder.get("response")
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            emit("eof")

    thread = threading.Thread(
        target=worker,
        name="crumbcontext-sse",
        daemon=True,
    )
    thread.start()
    try:
        while True:
            kind, value = await queue.get()
            if kind == "chunk":
                yield value
            elif kind == "error":
                raise value
            elif kind == "eof":
                break
    finally:
        stop.set()
        response = holder.get("response")
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


__all__ = [
    "AsyncSSESource",
    "HTTPStreamError",
    "SSEMessage",
    "decode_sse",
    "urllib_sse_source",
]
