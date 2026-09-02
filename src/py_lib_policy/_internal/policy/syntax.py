"""Shared Python syntax and declaration checks."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

from py_lib_policy._api.defaults import _IGNORED_PARTS
from py_lib_policy._internal.config.assembly import _read_toml
from py_lib_policy._internal.config.models import ProjectPolicyConfig
from py_lib_policy._internal.config.validation import _table
from py_lib_policy._internal.policy.models import Violation


def _parse(path: Path) -> ast.Module | None:
    """Parse one Python module, returning None for unreadable source."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def _iter_python(root: Path) -> Iterable[Path]:
    """Yield policy-relevant Python files beneath one root."""
    for path in sorted(root.rglob("*.py")):
        if not any(part in _IGNORED_PARTS for part in path.parts):
            yield path


def _doc_or_future(node: ast.stmt) -> bool:
    """Return whether one statement is a docstring or future import."""
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ) or (isinstance(node, ast.ImportFrom) and node.module == "__future__")


def _constant_assignment(node: ast.stmt) -> bool:
    """Return whether one statement assigns only uppercase names."""
    targets: list[ast.expr]
    if isinstance(node, ast.Assign):
        targets = list(node.targets)
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    else:
        return False
    return all(
        isinstance(target, ast.Name) and target.id.isupper() for target in targets
    )


def _exception_class(node: ast.ClassDef) -> bool:
    """Return whether one class derives from an exception-like base."""
    return any(
        _class_base_name(base).endswith(("Error", "Exception")) for base in node.bases
    )


def _class_base_name(base: ast.expr) -> str:
    """Return the final name segment for one class base expression."""
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return ""


def _allowed_root_statement(node: ast.stmt, package: str) -> bool:
    """Return whether one statement belongs in a package initializer."""
    if _doc_or_future(node):
        return True
    if isinstance(node, ast.ImportFrom):
        return _allowed_root_import_from(node, package)
    if isinstance(node, ast.Import):
        return all(alias.name == "importlib.metadata" for alias in node.names)
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        return _allowed_root_assignment(node)
    if isinstance(node, ast.Try):
        return _allowed_root_try(node, package)
    return False


def _allowed_root_import_from(node: ast.ImportFrom, package: str) -> bool:
    """Return whether an import-from statement belongs in the package root."""
    if node.module == "importlib.metadata":
        return True
    api_root = f"{package}._api"
    return node.module is not None and (
        node.module == api_root or node.module.startswith(f"{api_root}.")
    )


def _allowed_root_assignment(node: ast.Assign | ast.AnnAssign) -> bool:
    """Return whether a package-root assignment targets public metadata."""
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return all(
        isinstance(target, ast.Name) and target.id in {"__all__", "__version__"}
        for target in targets
    )


def _allowed_root_try(node: ast.Try, package: str) -> bool:
    """Return whether every statement in a package-root try block is allowed."""
    nested = [*node.body, *node.orelse, *node.finalbody]
    nested.extend(statement for handler in node.handlers for statement in handler.body)
    return all(_allowed_root_statement(statement, package) for statement in nested)


def _check_console_scripts(root: Path, config: ProjectPolicyConfig) -> list[Violation]:
    """Check console-script declarations against the public CLI facade."""
    raw = _read_toml(root / "pyproject.toml")
    scripts = _table(_table(raw.get("project")).get("scripts"))
    facade = root / "src" / config.primary_package / "_api" / "cli.py"
    tree = _parse(facade) if facade.is_file() else None
    functions = {
        node.name
        for node in (tree.body if tree else ())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    violations = (
        _console_script_violation(
            root=root,
            config=config,
            functions=functions,
            name=name,
            target=target,
        )
        for name, target in sorted(scripts.items())
    )
    return [violation for violation in violations if violation is not None]


def _console_script_violation(
    *,
    root: Path,
    config: ProjectPolicyConfig,
    functions: set[str],
    name: str,
    target: object,
) -> Violation | None:
    """Return the violation for one declared console script, if any."""
    prefix = f"{config.primary_package}._api.cli:"
    facade = root / "src" / config.primary_package / "_api" / "cli.py"
    if not isinstance(target, str) or not target.startswith(prefix):
        return Violation(
            root / "pyproject.toml",
            f"project scripts must target `{prefix}*`",
        )
    if not facade.is_file():
        return Violation(facade, "project scripts require an `_api/cli.py` facade")
    function = target.partition(":")[2]
    if function not in functions:
        return Violation(
            facade,
            f"project script `{name}` target function is missing from `_api/cli.py`",
        )
    return None


def _check_root_initializer(path: Path, package: str) -> list[Violation]:
    """Check one root package initializer against the public boundary."""
    tree = _parse(path) if path.is_file() else None
    if tree is None:
        return [Violation(path, "root package __init__.py must exist and parse")]
    return [
        Violation(
            path,
            "root __init__.py may contain only declaration/facade imports",
            node.lineno,
        )
        for node in tree.body
        if not _allowed_root_statement(node, package)
    ]


def _check_declaration_module(path: Path) -> list[Violation]:
    """Check one required public declaration module."""
    tree = _parse(path)
    if tree is None:
        return [Violation(path, "could not parse `_api` declaration module")]
    message = _declaration_message(path.name)
    return [
        Violation(path, message, node.lineno)
        for node in tree.body
        if not _declaration_statement_allowed(path.name, node)
    ]


def _declaration_message(filename: str) -> str:
    """Return the policy message for one declaration module kind."""
    messages = {
        "__init__.py": (
            "`_api/__init__.py` must stay empty except docstring/future import"
        ),
        "config.py": "`_api/config.py` must contain imports only",
        "defaults.py": "`_api/defaults.py` must contain constants only",
        "errors.py": "`_api/errors.py` must contain public exception classes only",
        "types.py": "`_api/types.py` must contain public type declarations only",
    }
    return messages[filename]


def _declaration_statement_allowed(filename: str, node: ast.stmt) -> bool:
    """Return whether one statement belongs in a declaration module."""
    if _doc_or_future(node):
        return True
    checks = {
        "__init__.py": _never_allowed,
        "config.py": _config_statement_allowed,
        "defaults.py": _defaults_statement_allowed,
        "errors.py": _errors_statement_allowed,
        "types.py": _types_statement_allowed,
    }
    return checks[filename](node)


def _never_allowed(node: ast.stmt) -> bool:
    """Reject non-documentation statements in empty declaration modules."""
    _ = node
    return False


def _config_statement_allowed(node: ast.stmt) -> bool:
    """Return whether one statement belongs in public config declarations."""
    return isinstance(node, ast.ImportFrom)


def _defaults_statement_allowed(node: ast.stmt) -> bool:
    """Return whether one statement belongs in public defaults declarations."""
    return isinstance(node, (ast.Import, ast.ImportFrom)) or _constant_assignment(node)


def _errors_statement_allowed(node: ast.stmt) -> bool:
    """Return whether one statement belongs in public error declarations."""
    return isinstance(node, (ast.Import, ast.ImportFrom)) or (
        isinstance(node, ast.ClassDef) and _exception_class(node)
    )


def _types_statement_allowed(node: ast.stmt) -> bool:
    """Return whether one statement belongs in public type declarations."""
    return isinstance(
        node,
        (
            ast.Import,
            ast.ImportFrom,
            ast.Assign,
            ast.AnnAssign,
            ast.ClassDef,
            ast.TypeAlias,
        ),
    )
