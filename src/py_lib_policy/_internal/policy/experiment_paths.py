"""Engineering Experiment filesystem-path isolation checks."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path, PurePath

from py_lib_policy._api.defaults import _IGNORED_PARTS
from py_lib_policy._internal.policy.models import Violation


def _check_capsule_paths(capsule: Path) -> list[Violation]:
    """Reject statically visible path expressions that escape a capsule."""
    violations: list[Violation] = []
    for path in _iter_python(capsule / "src"):
        tree = _parse_python(path)
        if tree is None:
            continue
        allowed_parent_index = len(path.parent.relative_to(capsule).parts)
        for node in ast.walk(tree):
            if _escapes_via_file_parents(node, allowed_parent_index):
                message = (
                    "experiment path derived from `__file__` must not escape capsule"
                )
                violations.append(
                    Violation(path, message, getattr(node, "lineno", None))
                )
            literal = _path_constructor_literal(node)
            if literal is not None and _literal_path_escapes(literal):
                violations.append(
                    Violation(
                        path,
                        f"experiment Path literal must stay inside capsule: {literal}",
                        getattr(node, "lineno", None),
                    )
                )
    return violations


def _escapes_via_file_parents(node: ast.AST, allowed_parent_index: int) -> bool:
    """Return whether one `__file__` parents lookup climbs above capsule root."""
    if not isinstance(node, ast.Subscript):
        return False
    if not isinstance(node.value, ast.Attribute) or node.value.attr != "parents":
        return False
    if not _contains_file_name(node.value.value):
        return False
    index = _constant_nonnegative_int(node.slice)
    return index is not None and index > allowed_parent_index


def _contains_file_name(node: ast.AST) -> bool:
    """Return whether an expression is rooted in the `__file__` name."""
    return any(
        isinstance(item, ast.Name) and item.id == "__file__" for item in ast.walk(node)
    )


def _constant_nonnegative_int(node: ast.AST) -> int | None:
    """Return one literal non-negative integer subscript."""
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and node.value >= 0
    ):
        return node.value
    return None


def _path_constructor_literal(node: ast.AST) -> str | None:
    """Return a literal passed directly to pathlib-style `Path(...)`."""
    if not isinstance(node, ast.Call) or not node.args:
        return None
    function = node.func
    name = function.id if isinstance(function, ast.Name) else None
    if name not in {"Path", "PurePath"}:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _literal_path_escapes(value: str) -> bool:
    """Return whether a literal is absolute or contains parent traversal."""
    path = PurePath(value)
    return path.is_absolute() or ".." in path.parts


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
