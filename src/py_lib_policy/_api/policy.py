"""Public policy checking facade."""

from __future__ import annotations

from pathlib import Path

from py_lib_policy._internal import Violation, check as _check


def check(*, start: Path | None = None) -> tuple[Violation, ...]:
    """Return every policy violation for a standalone project or uv workspace."""
    return _check(start=start)
