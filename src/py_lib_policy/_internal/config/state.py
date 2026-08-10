"""Discover standalone and uv-workspace project roots."""

from __future__ import annotations

from pathlib import Path

from py_lib_policy._internal.config.assembly import _read_toml
from py_lib_policy._internal.config.validation import _table


def _normalize_start(start: Path | None) -> Path:
    """Return the resolved starting path for project discovery."""
    return (start or Path.cwd()).expanduser().resolve()


def _find_pyproject(start: Path | None = None) -> Path:
    """Find the nearest pyproject.toml above a starting path."""
    candidate = _normalize_start(start)
    if candidate.is_file():
        candidate = candidate.parent
    for root in (candidate, *candidate.parents):
        path = root / "pyproject.toml"
        if path.is_file():
            return path
    msg = f"Could not find pyproject.toml above {candidate}."
    raise FileNotFoundError(msg)


def discover_project_roots(*, start: Path | None = None) -> tuple[Path, ...]:
    """Return standalone or uv-workspace project roots."""
    pyproject = _find_pyproject(start)
    root = pyproject.parent
    raw = _read_toml(pyproject)
    members = _table(_table(raw.get("tool")).get("uv"))
    workspace = _table(members.get("workspace"))
    values = workspace.get("members")
    if not isinstance(values, list):
        return (root,)
    roots = tuple(
        root / item.strip() for item in values if isinstance(item, str) and item.strip()
    )
    return roots or (root,)
