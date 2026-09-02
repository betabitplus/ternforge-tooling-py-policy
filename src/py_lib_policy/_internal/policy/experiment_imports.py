"""Engineering Experiment import-isolation checks."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

from py_lib_policy._api.defaults import _IGNORED_PARTS
from py_lib_policy._internal.config.models import ProjectPolicyConfig
from py_lib_policy._internal.policy.models import Violation

_FORBIDDEN_EXPERIMENT_IMPORT_ROOTS = {"experiments", "src", "tests"}


def _check_capsule_imports(
    capsule: Path,
    config: ProjectPolicyConfig,
) -> list[Violation]:
    """Reject imports from the parent project and other experiment namespaces."""
    forbidden = {
        *_FORBIDDEN_EXPERIMENT_IMPORT_ROOTS,
        *config.package_names,
    }
    violations: list[Violation] = []
    for path in _iter_python(capsule / "src"):
        tree = _parse_python(path)
        if tree is None:
            continue
        for name, line in _import_names(tree):
            root = name.split(".", 1)[0]
            if root in forbidden:
                message = (
                    f"experiment must not import parent/sibling project code: {name}"
                )
                violations.append(Violation(path, message, line))
    return violations


def _check_product_does_not_import_experiments(root: Path) -> list[Violation]:
    """Keep shipped code, tests, and examples independent of experiments."""
    violations: list[Violation] = []
    for zone in (root / "src", root / "tests", root / "examples"):
        for path in _iter_python(zone):
            tree = _parse_python(path)
            if tree is None:
                continue
            for name, line in _import_names(tree):
                if name == "experiments" or name.startswith("experiments."):
                    violations.append(
                        Violation(
                            path,
                            "product/tests/examples must not import experiments",
                            line,
                        )
                    )
    return violations


def _iter_python(root: Path) -> Iterable[Path]:
    """Yield Python files below a root while ignoring ephemeral directories."""
    if not root.is_dir():
        return ()
    return (
        path
        for path in sorted(root.rglob("*.py"))
        if path.is_file()
        and not any(part in _IGNORED_PARTS for part in path.relative_to(root).parts)
    )


def _parse_python(path: Path) -> ast.Module | None:
    """Parse Python when possible; syntax validation belongs to generic tooling."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def _import_names(tree: ast.AST) -> Iterable[tuple[str, int]]:
    """Yield absolute import names and source lines from one syntax tree."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module, node.lineno
