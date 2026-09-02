"""Engineering Experiment capsule filesystem and orchestration checks."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from py_lib_policy._api.defaults import _IGNORED_PARTS
from py_lib_policy._internal.config.models import ProjectPolicyConfig
from py_lib_policy._internal.policy.experiment_dependencies import (
    _check_capsule_dependencies,
)
from py_lib_policy._internal.policy.experiment_imports import (
    _check_capsule_imports,
    _check_product_does_not_import_experiments,
)
from py_lib_policy._internal.policy.models import Violation

_CAPSULE_RE = re.compile(r"^exp_[0-9]{4}_[a-z0-9_]+$")
_REQUIRED_CAPSULE_FILES = (
    "src/experiment.py",
    "report/report.ipynb",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
)
_FORBIDDEN_NAMESPACE_DIRS = {"_support", "shared"}


def _check_experiments(
    root: Path,
    config: ProjectPolicyConfig,
) -> list[Violation]:
    """Check optional Engineering Experiment capsules and legacy boundaries."""
    violations = _check_legacy_workbench(root)
    experiments = root / "experiments"
    if not experiments.exists():
        return violations
    if not experiments.is_dir():
        violations.append(Violation(experiments, "experiments must be a directory"))
        return violations

    violations.extend(_check_experiment_namespace(experiments, config))
    violations.extend(_check_product_does_not_import_experiments(root))
    return violations


def _check_legacy_workbench(root: Path) -> list[Violation]:
    """Reject the superseded manual-probe storage convention."""
    workbench = root / "workbench"
    if not workbench.exists():
        return []
    return [
        Violation(
            workbench,
            "legacy `workbench/` is forbidden; use self-contained Engineering "
            "Experiment capsules under `experiments/`",
        )
    ]


def _check_experiment_namespace(
    experiments: Path,
    config: ProjectPolicyConfig,
) -> list[Violation]:
    """Validate project namespaces and their capsules."""
    violations: list[Violation] = []
    initializer = experiments / "__init__.py"
    if initializer.exists():
        violations.append(
            Violation(
                initializer,
                "experiments is a filesystem zone, not a shared Python package",
            )
        )

    for path in _visible_children(experiments):
        if path.is_file():
            if path.suffix == ".py":
                violations.append(
                    Violation(
                        path,
                        "loose experiment Python must live inside a capsule",
                    )
                )
            continue
        if not path.is_dir():
            continue
        if path.name in _FORBIDDEN_NAMESPACE_DIRS:
            violations.append(
                Violation(path, "shared experiment code directories are forbidden")
            )
            continue
        violations.extend(_check_project_namespace(path, config))
    return violations


def _check_project_namespace(
    project: Path,
    config: ProjectPolicyConfig,
) -> list[Violation]:
    """Validate one `experiments/<project>/` namespace."""
    violations: list[Violation] = []
    initializer = project / "__init__.py"
    if initializer.exists():
        violations.append(
            Violation(
                initializer,
                "experiment project namespaces must not be Python packages",
            )
        )

    for path in _visible_children(project):
        if path.is_file():
            if path.suffix == ".py":
                violations.append(
                    Violation(
                        path,
                        "loose experiment Python must live inside a capsule",
                    )
                )
            continue
        if not path.is_dir():
            continue
        if path.name in _FORBIDDEN_NAMESPACE_DIRS:
            violations.append(
                Violation(path, "shared experiment code directories are forbidden")
            )
            continue
        if not _CAPSULE_RE.fullmatch(path.name):
            violations.append(
                Violation(
                    path,
                    "experiment capsule directory must match `exp_####_<slug>`",
                )
            )
            continue
        violations.extend(_check_capsule(path, config))
    return violations


def _check_capsule(capsule: Path, config: ProjectPolicyConfig) -> list[Violation]:
    """Validate one self-contained Engineering Experiment capsule."""
    violations: list[Violation] = []
    for relative in _REQUIRED_CAPSULE_FILES:
        path = capsule / relative
        if not path.is_file():
            violations.append(
                Violation(path, "required experiment capsule file is missing")
            )

    violations.extend(
        Violation(optional_dir, "experiment inputs/artifacts must be directories")
        for optional_dir in (capsule / "inputs", capsule / "artifacts")
        if optional_dir.exists() and not optional_dir.is_dir()
    )
    violations.extend(_check_capsule_python_locations(capsule))
    violations.extend(_check_nested_capsules(capsule))
    violations.extend(_check_symlinks(capsule))
    violations.extend(_check_capsule_dependencies(capsule, config))
    violations.extend(_check_capsule_imports(capsule, config))
    return violations


def _check_capsule_python_locations(capsule: Path) -> list[Violation]:
    """Keep all executable capsule Python under `src/`."""
    violations: list[Violation] = []
    for path in _iter_files(capsule, suffix=".py"):
        relative = path.relative_to(capsule)
        if relative.parts and relative.parts[0] != "src":
            violations.append(
                Violation(path, "experiment Python source must live under `src/`")
            )

    canonical = capsule / "src" / "experiment.py"
    violations.extend(
        Violation(
            path,
            "capsule must expose exactly one canonical `src/experiment.py`",
        )
        for path in _iter_files(capsule / "src", suffix=".py")
        if path.name == "experiment.py" and path != canonical
    )
    return violations


def _check_nested_capsules(capsule: Path) -> list[Violation]:
    """Reject capsules nested inside another capsule."""
    return [
        Violation(path, "nested experiment capsules are forbidden")
        for path in _iter_dirs(capsule)
        if path != capsule and _CAPSULE_RE.fullmatch(path.name)
    ]


def _check_symlinks(capsule: Path) -> list[Violation]:
    """Reject symlinks that escape the capsule filesystem boundary."""
    violations: list[Violation] = []
    capsule_root = capsule.resolve()
    for path in capsule.rglob("*"):
        relative = path.relative_to(capsule)
        if (
            any(part in _IGNORED_PARTS for part in relative.parts)
            or not path.is_symlink()
        ):
            continue
        try:
            path.resolve().relative_to(capsule_root)
        except (OSError, ValueError):
            violations.append(
                Violation(path, "experiment symlink must not escape capsule")
            )
    return violations


def _visible_children(root: Path) -> Iterable[Path]:
    """Yield direct children excluding ephemeral policy-ignored directories."""
    if not root.is_dir():
        return ()
    return (
        path
        for path in sorted(root.iterdir())
        if path.name not in _IGNORED_PARTS and path.name != ".DS_Store"
    )


def _iter_files(root: Path, *, suffix: str) -> Iterable[Path]:
    """Yield files below a root while ignoring ephemeral directories."""
    if not root.is_dir():
        return ()
    return (
        path
        for path in sorted(root.rglob(f"*{suffix}"))
        if path.is_file()
        and not any(part in _IGNORED_PARTS for part in path.relative_to(root).parts)
    )


def _iter_dirs(root: Path) -> Iterable[Path]:
    """Yield directories below a root while ignoring ephemeral directories."""
    if not root.is_dir():
        return ()
    return (
        path
        for path in sorted(root.rglob("*"))
        if path.is_dir()
        and not any(part in _IGNORED_PARTS for part in path.relative_to(root).parts)
    )
