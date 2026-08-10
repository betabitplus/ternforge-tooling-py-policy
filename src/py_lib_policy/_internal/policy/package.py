"""Package, facade, and example policy checks."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

from py_lib_policy._api.defaults import _REQUIRED_API_FILES, _REQUIRED_CONFIG_FILES
from py_lib_policy._internal.config.models import ProjectPolicyConfig
from py_lib_policy._internal.policy.models import Violation
from py_lib_policy._internal.policy.syntax import (
    _check_declaration_module,
    _check_root_initializer,
    _has_cell_marker,
    _iter_python,
    _parse,
)


def _check_product_facade(path: Path) -> list[Violation]:
    """Check that one product API module defines a public facade."""
    tree = _parse(path)
    if tree is None:
        return [Violation(path, "could not parse `_api` module")]
    definitions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and not node.name.startswith("_")
    ]
    return (
        []
        if definitions
        else [
            Violation(
                path,
                "product `_api` modules must define facades, not re-export wrappers",
            )
        ]
    )


def _assigns_all(node: ast.stmt) -> bool:
    """Return whether one statement assigns the __all__ declaration."""
    if isinstance(node, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    return (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "__all__"
    )


def _check_package(
    root: Path, package: str, config: ProjectPolicyConfig
) -> list[Violation]:
    """Check one managed package layout and public/private boundaries."""
    package_root = root / "src" / package
    violations = [
        Violation(path, "required Ternforge package path is missing")
        for path in _required_package_paths(package_root)
        if not path.exists()
    ]
    violations.extend(_check_root_initializer(package_root / "__init__.py", package))
    violations.extend(_check_package_root_children(package_root, config))
    violations.extend(_check_internal_layout(package_root / "_internal"))
    violations.extend(_check_api_layout(package_root / "_api"))
    violations.extend(_check_all_declarations(package_root))
    return violations


def _required_package_paths(package_root: Path) -> tuple[Path, ...]:
    """Return every required path for one managed package."""
    required = [
        package_root / "__init__.py",
        package_root / "py.typed",
        package_root / "_api",
        package_root / "_internal",
        package_root / "_internal" / "__init__.py",
    ]
    required.extend(package_root / "_api" / item for item in _REQUIRED_API_FILES)
    required.extend(
        package_root / "_internal" / "config" / item for item in _REQUIRED_CONFIG_FILES
    )
    return tuple(required)


def _check_package_root_children(
    package_root: Path, config: ProjectPolicyConfig
) -> list[Violation]:
    """Check public-looking files and directories at one package root."""
    if not package_root.is_dir():
        return []
    allowed_dirs = {"_api", "_internal", *config.public_namespace_packages}
    violations = (
        _package_root_child_violation(child, allowed_dirs=allowed_dirs)
        for child in sorted(package_root.iterdir())
        if child.name != "__pycache__"
    )
    return [violation for violation in violations if violation is not None]


def _package_root_child_violation(
    child: Path, *, allowed_dirs: set[str]
) -> Violation | None:
    """Return the public-layout violation for one package-root child."""
    if child.is_file() and child.name not in {"__init__.py", "py.typed"}:
        return Violation(
            child,
            "public-looking root module must live under `_api` or `_internal`",
        )
    if child.is_dir() and child.name not in allowed_dirs:
        return Violation(
            child,
            (
                "public-looking root package must be declared or moved under "
                "`_api`/`_internal`"
            ),
        )
    return None


def _check_internal_layout(internal: Path) -> list[Violation]:
    """Check that private implementation modules live below subpackages."""
    if not internal.is_dir():
        return []
    return [
        Violation(
            path,
            "private implementation modules must live in `_internal` subpackages",
        )
        for path in sorted(internal.glob("*.py"))
        if path.name != "__init__.py"
    ]


def _check_api_layout(api_root: Path) -> list[Violation]:
    """Check declaration and product facade modules under `_api`."""
    if not api_root.is_dir():
        return []
    violations: list[Violation] = []
    for path in sorted(api_root.glob("*.py")):
        checker = (
            _check_declaration_module
            if path.name in _REQUIRED_API_FILES
            else _check_product_facade
        )
        violations.extend(checker(path))
    return violations


def _check_all_declarations(package_root: Path) -> list[Violation]:
    """Check that `__all__` appears only in the package-root initializer."""
    root_init = package_root / "__init__.py"
    violations: list[Violation] = []
    for path in _iter_python(package_root):
        if path != root_init:
            violations.extend(_all_declaration_violations(path))
    return violations


def _all_declaration_violations(path: Path) -> list[Violation]:
    """Return misplaced `__all__` declarations from one Python module."""
    tree = _parse(path)
    if tree is None:
        return []
    return [
        Violation(path, "`__all__` must be declared only in root package", node.lineno)
        for node in tree.body
        if _assigns_all(node)
    ]


def _check_dynamic_private_imports(
    root: Path, packages: Iterable[str]
) -> list[Violation]:
    """Check Python files for string-based private imports."""
    prefixes = tuple(f"{package}._internal" for package in packages)
    violations: list[Violation] = []
    for path in _iter_python(root):
        violations.extend(_dynamic_private_import_violations(path, prefixes=prefixes))
    return violations


def _dynamic_private_import_violations(
    path: Path, *, prefixes: tuple[str, ...]
) -> list[Violation]:
    """Return string-based private imports from one Python module."""
    tree = _parse(path)
    if tree is None:
        return []
    return [
        Violation(
            path,
            "string-based dynamic import of `_internal` is forbidden",
            node.lineno,
        )
        for node in ast.walk(tree)
        if _is_private_dynamic_import(node, prefixes=prefixes)
    ]


def _is_private_dynamic_import(node: ast.AST, *, prefixes: tuple[str, ...]) -> bool:
    """Return whether one AST node dynamically imports a private package."""
    if not isinstance(node, ast.Call) or not node.args:
        return False
    if _called_name(node.func) not in {"__import__", "importlib.import_module"}:
        return False
    first = node.args[0]
    return (
        isinstance(first, ast.Constant)
        and isinstance(first.value, str)
        and first.value.startswith(prefixes)
    )


def _called_name(node: ast.expr) -> str:
    """Return a simple dotted call target name when statically available."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    return ""


def _check_examples(root: Path, packages: tuple[str, ...]) -> list[Violation]:
    """Check example layout, runnability, and public-boundary use."""
    examples = root / "examples"
    if not examples.exists():
        return []
    if not examples.is_dir():
        return [Violation(examples, "examples must be a directory")]
    meaningful = [child for child in examples.iterdir() if child.name != "__pycache__"]
    if not meaningful:
        return []
    violations = _check_example_root_children(meaningful, packages=packages)
    for package in packages:
        violations.extend(_check_example_package(examples / package, package=package))
    return violations


def _check_example_root_children(
    children: Iterable[Path], *, packages: tuple[str, ...]
) -> list[Violation]:
    """Check the immediate layout beneath the examples root."""
    package_names = set(packages)
    return [
        Violation(child, "examples must live under `examples/<package>/`")
        for child in sorted(children)
        if not _allowed_example_root_child(child, package_names=package_names)
    ]


def _allowed_example_root_child(child: Path, *, package_names: set[str]) -> bool:
    """Return whether one immediate examples child belongs in the layout."""
    if child.is_file():
        return child.name == "__init__.py"
    return child.name in package_names


def _check_example_package(package_root: Path, *, package: str) -> list[Violation]:
    """Check runnable examples for one package."""
    if not package_root.is_dir():
        return []
    violations: list[Violation] = []
    for path in sorted(package_root.rglob("*.py")):
        violations.extend(_check_example_file(path, package=package))
    return violations


def _check_example_file(path: Path, *, package: str) -> list[Violation]:
    """Check one example module for runnability and public-boundary use."""
    violations: list[Violation] = []
    if path.name != "__init__.py" and not _has_cell_marker(path):
        violations.append(
            Violation(
                path,
                ("runnable examples must start with `# %%` for IPython console use"),
            )
        )
    tree = _parse(path)
    if tree is None:
        return [*violations, Violation(path, "example source must be valid Python")]
    violations.extend(
        _private_example_reference_violations(path, tree, package=package)
    )
    return violations


def _private_example_reference_violations(
    path: Path, tree: ast.Module, *, package: str
) -> list[Violation]:
    """Return string references to private modules from one example."""
    prefixes = ("src", f"{package}._api", f"{package}._internal")
    return [
        Violation(
            path,
            "examples must not reference private package modules",
            node.lineno,
        )
        for node in ast.walk(tree)
        if _private_example_reference(node, prefixes=prefixes)
    ]


def _private_example_reference(node: ast.AST, *, prefixes: tuple[str, ...]) -> bool:
    """Return whether an AST node contains one private-module string."""
    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
        return False
    return any(
        node.value == prefix or node.value.startswith(f"{prefix}.")
        for prefix in prefixes
    )
