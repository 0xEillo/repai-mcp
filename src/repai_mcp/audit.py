"""Append-only JSONL audit log for every tool invocation."""

from __future__ import annotations

import functools
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class AuditLogger:
    def __init__(self, path: Path, mode: str) -> None:
        self._path = path
        self._mode = mode

    @property
    def path(self) -> Path:
        return self._path

    def record(
        self,
        *,
        tool: str,
        arguments: dict[str, Any],
        duration_ms: float,
        status: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "arguments": arguments,
            "mode": self._mode,
            "duration_ms": round(duration_ms, 2),
            "status": status,
        }
        if error is not None:
            entry["error"] = error

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")
        return entry

    def audited(self, fn: F) -> F:
        """Wrap a tool function so every call is recorded, including failures."""

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                self.record(
                    tool=fn.__name__,
                    arguments=kwargs,
                    duration_ms=(time.perf_counter() - start) * 1000,
                    status="error",
                    error=str(exc),
                )
                raise
            self.record(
                tool=fn.__name__,
                arguments=kwargs,
                duration_ms=(time.perf_counter() - start) * 1000,
                status="ok",
            )
            return result

        return wrapper  # type: ignore[return-value]
