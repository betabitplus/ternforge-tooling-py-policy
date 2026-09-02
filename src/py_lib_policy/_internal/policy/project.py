"""Repository-level managed project policy checks."""

from __future__ import annotations

from pathlib import Path

from py_lib_policy._api.defaults import _REQUIRED_MANAGED_PROJECT_FILES
from py_lib_policy._internal.policy.models import Violation


def _check_managed_project_files(root: Path) -> list[Violation]:
    """Check mandatory template-managed project control files."""
    return [
        Violation(root / relative, "required Ternforge managed project file is missing")
        for relative in _REQUIRED_MANAGED_PROJECT_FILES
        if not (root / relative).is_file()
    ]
