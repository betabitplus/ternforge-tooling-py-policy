"""Public policy checking and command-line entry points."""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

from py_lib_policy._internal.config import (
    _normalize_start,
    _project_config,
    discover_project_roots,
)
from py_lib_policy._internal.policy.models import Violation
from py_lib_policy._internal.policy.package import (
    _check_dynamic_private_imports,
    _check_examples,
    _check_package,
)
from py_lib_policy._internal.policy.project import (
    _check_docs,
    _check_tests,
    _check_workbench,
)
from py_lib_policy._internal.policy.syntax import _check_console_scripts


def check_project_root(root: Path) -> tuple[Violation, ...]:
    """Return every policy violation for one project root."""
    root = root.resolve()
    try:
        config = _project_config(root)
    except (OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
        return (Violation(root / "pyproject.toml", str(exc)),)
    violations: list[Violation] = []
    violations.extend(_check_console_scripts(root, config))
    for package in config.package_names:
        violations.extend(_check_package(root, package, config))
    violations.extend(_check_dynamic_private_imports(root, config.package_names))
    violations.extend(_check_examples(root, config.package_names))
    violations.extend(_check_tests(root, config.package_names))
    violations.extend(_check_workbench(root))
    violations.extend(_check_docs(root, config))
    return tuple(
        sorted(
            violations, key=lambda item: (str(item.path), item.line or 0, item.message)
        )
    )


def check(*, start: Path | None = None) -> tuple[Violation, ...]:
    """Return every policy violation for a standalone project or uv workspace."""
    try:
        roots = discover_project_roots(start=start)
    except (OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
        path = _normalize_start(start) / "pyproject.toml"
        return (Violation(path, str(exc)),)
    violations: list[Violation] = []
    for root in roots:
        violations.extend(check_project_root(root))
    return tuple(
        sorted(
            violations, key=lambda item: (str(item.path), item.line or 0, item.message)
        )
    )


def main(argv: list[str] | None = None) -> int:
    """Run the policy command-line interface and return its exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.resolve()
    violations = check(start=root)
    for violation in violations:
        print(violation.render(root))
    return 1 if violations else 0
