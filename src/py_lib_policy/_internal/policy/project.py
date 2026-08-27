"""Test, workbench, and documentation policy checks."""

from __future__ import annotations

from pathlib import Path

from py_lib_policy._api.defaults import _REQUIRED_MANAGED_PROJECT_FILES
from py_lib_policy._internal.policy.models import Violation
from py_lib_policy._internal.policy.syntax import _has_cell_marker


def _check_managed_project_files(root: Path) -> list[Violation]:
    """Check mandatory template-managed project control files."""
    return [
        Violation(root / relative, "required Ternforge managed project file is missing")
        for relative in _REQUIRED_MANAGED_PROJECT_FILES
        if not (root / relative).is_file()
    ]


def _check_workbench(root: Path) -> list[Violation]:
    """Check optional workbench modules for interactive runnability."""
    workbench = root / "workbench"
    if not workbench.exists():
        return []
    if not workbench.is_dir():
        return [Violation(workbench, "workbench must be a directory")]
    return [
        Violation(
            path,
            "runnable workbench modules must start with `# %%` for IPython console use",
        )
        for path in sorted(workbench.rglob("*.py"))
        if path.name != "__init__.py" and not _has_cell_marker(path)
    ]
