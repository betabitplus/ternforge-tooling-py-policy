"""Test, workbench, and documentation policy checks."""

from __future__ import annotations

from pathlib import Path

import yaml

from py_lib_policy._api.defaults import (
    _ANSWERS_FILE,
    _PACKAGE_DOCS,
    _PACKAGE_PLACEHOLDER,
    _REQUIRED_MANAGED_PROJECT_FILES,
    _REQUIRED_PACKAGE_TEST_PATHS,
    _REQUIRED_TEMPLATE_TEST_PATHS,
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
    """Check required test layout and runnable e2e markers."""
    tests = root / "tests"
    required = _required_test_paths(tests, packages=packages)
    violations = [
        Violation(path, "required Ternforge test path is missing")
        for path in required
        if not path.exists()
    ]
    for package in packages:
        violations.extend(_e2e_marker_violations(tests / package / "e2e"))
    return violations


def _required_test_paths(tests: Path, *, packages: tuple[str, ...]) -> list[Path]:
    """Return all required root and package-specific test paths."""
    required = [tests / item for item in _REQUIRED_TEST_ROOT_PATHS]
    for package in packages:
        package_root = tests / package
        required.extend(package_root / item for item in _REQUIRED_PACKAGE_TEST_PATHS)
        required.extend(package_root / item for item in _REQUIRED_TEMPLATE_TEST_PATHS)
    return required


def _e2e_marker_violations(e2e: Path) -> list[Violation]:
    """Return missing interactive cell markers below one e2e directory."""
    if not e2e.is_dir():
        return []
    return [
        Violation(
            path,
            "runnable e2e tests must start with `# %%` for IPython console use",
        )
        for path in sorted(e2e.rglob("*.py"))
        if path.name != "__init__.py" and not _has_cell_marker(path)
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


def _load_e2e_slices(root: Path) -> tuple[tuple[str, Path], ...]:
    """Load validated e2e slice declarations from Copier answers."""
    answers = root / _ANSWERS_FILE
    if not answers.is_file():
        return ()
    value = yaml.safe_load(answers.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        msg = f"{_ANSWERS_FILE} must contain a mapping"
        raise TypeError(msg)
    raw = value.get("e2e_slices", ())
    if raw is None:
        return ()
    if not isinstance(raw, list):
        msg = f"{_ANSWERS_FILE} e2e_slices must be a list"
        raise TypeError(msg)
    return tuple(_parse_e2e_slice(item) for item in raw)


def _parse_e2e_slice(item: object) -> tuple[str, Path]:
    """Return one validated e2e slice declaration."""
    if not isinstance(item, dict):
        msg = f"{_ANSWERS_FILE} e2e_slices items must be mappings"
        raise TypeError(msg)
    name = _required_slice_text(item.get("name"), field="name")
    path = _required_slice_text(item.get("path"), field="path")
    normalized = Path(path)
    if normalized.is_absolute():
        msg = f"{_ANSWERS_FILE} e2e slice path must be relative"
        raise ValueError(msg)
    return name, normalized


def _required_slice_text(value: object, *, field: str) -> str:
    """Return one required normalized e2e slice string."""
    if not isinstance(value, str) or not value.strip():
        msg = f"{_ANSWERS_FILE} e2e slice {field} must be a non-empty string"
        raise ValueError(msg)
    return value.strip()


def _check_docs(root: Path, config: ProjectPolicyConfig) -> list[Violation]:
    """Check required documentation and configured e2e slice evidence."""
    required = [root / "docs" / "README.md"]
    for package in config.package_names:
        docs = root / "docs" / package
        required.extend(docs / item for item in _PACKAGE_DOCS)
    violations = [
        Violation(path, "required Ternforge docs file is missing")
        for path in required
        if not path.is_file()
    ]
    try:
        slices = _load_e2e_slices(root)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        return [*violations, Violation(root / _ANSWERS_FILE, str(exc))]
    for name, path in slices:
        resolved = Path(str(path).replace(_PACKAGE_PLACEHOLDER, config.primary_package))
        if not (root / resolved).is_dir():
            violations.append(
                Violation(root / resolved, "configured e2e slice directory is missing")
            )
        doc = (
            root
            / "docs"
            / config.primary_package
            / "verification"
            / "e2e"
            / f"{name}.md"
        )
        if not doc.is_file():
            violations.append(
                Violation(doc, "configured e2e slice documentation is missing")
            )
    return violations
