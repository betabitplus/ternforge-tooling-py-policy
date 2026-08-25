"""Test, workbench, and documentation policy checks."""

from __future__ import annotations

from pathlib import Path

from py_lib_policy._api.defaults import (
    _PACKAGE_DOCS,
    _REQUIRED_MANAGED_PROJECT_FILES,
    _REQUIRED_PACKAGE_TEST_PATHS,
    _REQUIRED_TEST_ROOT_PATHS,
)
from py_lib_policy._internal.config.models import ProjectPolicyConfig
from py_lib_policy._internal.policy.models import Violation
from py_lib_policy._internal.policy.syntax import _has_cell_marker


def _check_managed_project_files(root: Path) -> list[Violation]:
    """Check mandatory template-managed project control files."""
    return [
        Violation(root / relative, "required Ternforge managed project file is missing")
        for relative in _REQUIRED_MANAGED_PROJECT_FILES
        if not (root / relative).is_file()
    ]


def _check_tests(root: Path, packages: tuple[str, ...]) -> list[Violation]:
    """Check the required generic test layout."""
    tests = root / "tests"
    required = _required_test_paths(tests, packages=packages)
    return [
        Violation(path, "required Ternforge test path is missing")
        for path in required
        if not path.exists()
    ]


def _required_test_paths(tests: Path, *, packages: tuple[str, ...]) -> list[Path]:
    """Return all required root and package-specific test paths."""
    required = [tests / item for item in _REQUIRED_TEST_ROOT_PATHS]
    for package in packages:
        package_root = tests / package
        required.extend(package_root / item for item in _REQUIRED_PACKAGE_TEST_PATHS)
    return required


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


def _check_docs(root: Path, config: ProjectPolicyConfig) -> list[Violation]:
    """Check required generic project documentation."""
    required = [root / "docs" / "README.md"]
    for package in config.package_names:
        docs = root / "docs" / package
        required.extend(docs / item for item in _PACKAGE_DOCS)
    return [
        Violation(path, "required Ternforge docs file is missing")
        for path in required
        if not path.is_file()
    ]
