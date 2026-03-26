"""
Persistent session storage for NexCode: conversation history plus metadata
so work can be resumed across runs with the same (or updated) workspace context.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


SESSION_VERSION = 1
DEFAULT_SESSION_FILENAME = ".nexcode_session.json"


class SessionLoadError(Exception):
    """Raised when the session file exists but cannot be parsed or validated."""


@dataclass
class SessionState:
    """Versioned on-disk format for save / resume."""

    version: int = SESSION_VERSION
    saved_at: str = ""
    provider: str | None = None
    model: str | None = None
    mode: str | None = None
    workspace: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionState:
        v = int(data.get("version", 0))
        messages = data.get("messages")
        if not isinstance(messages, list):
            messages = []
        return cls(
            version=v if v >= 0 else 0,
            saved_at=str(data.get("saved_at", "")),
            provider=_optional_str(data.get("provider")),
            model=_optional_str(data.get("model")),
            mode=_optional_str(data.get("mode")),
            workspace=_optional_str(data.get("workspace")),
            messages=[m for m in messages if isinstance(m, dict)],
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def get_session_path() -> str:
    return os.environ.get("NEXCODE_SESSION_FILE", DEFAULT_SESSION_FILENAME)


def ensure_json_serializable(obj: Any) -> Any:
    """Recursively coerce values so json.dump will not fail on nested structures."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): ensure_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [ensure_json_serializable(x) for x in obj]
    return str(obj)


def _atomic_write_json(path: str, payload: dict[str, Any]) -> None:
    path = os.path.abspath(path)
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=directory,
        prefix=".nexcode_session_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def load_session(path: str | None = None) -> SessionState:
    """
    Load session from disk. Missing file returns empty SessionState.
    Legacy format (bare JSON array of messages) is upgraded to SessionState.
    """
    path = path or get_session_path()
    if not os.path.exists(path):
        return SessionState()

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise SessionLoadError(f"Cannot read session file {path!r}: {e}") from e

    if isinstance(raw, list):
        return SessionState(
            version=0,
            messages=ensure_json_serializable([m for m in raw if isinstance(m, dict)]),
        )

    if isinstance(raw, dict):
        return SessionState.from_dict(raw)

    raise SessionLoadError(f"Unexpected session JSON shape in {path!r}")


def save_session_state(state: SessionState, path: str | None = None) -> None:
    """Persist session with atomic replace to avoid truncated files on crash."""
    path = path or get_session_path()
    state = SessionState(
        version=SESSION_VERSION,
        saved_at=datetime.now(timezone.utc).isoformat(),
        provider=state.provider,
        model=state.model,
        mode=state.mode,
        workspace=state.workspace,
        messages=ensure_json_serializable(state.messages),
    )
    _atomic_write_json(path, state.to_dict())


def delete_session_file(path: str | None = None) -> None:
    path = path or get_session_path()
    try:
        os.remove(path)
    except OSError:
        pass


def describe_session(state: SessionState) -> str:
    """One-line summary for the resume prompt."""
    n = len(state.messages)
    when = state.saved_at or "unknown time"
    ws = state.workspace or "(no path)"
    return f"{n} messages · saved {when} · workspace {ws}"
