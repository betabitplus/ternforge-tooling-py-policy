"""Policy models, constants, and project discovery."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_TOOL_TABLE = "ternforge"

_ANSWERS_FILE = "_copier_answers.yml"

_PACKAGE_PLACEHOLDER = "__PACKAGE_NAME__"

_IGNORED_PARTS = {".git", ".venv", "build", "dist", "__pycache__"}

_REQUIRED_API_FILES = (
    "__init__.py",
    "config.py",
    "defaults.py",
    "errors.py",
    "types.py",
)

_REQUIRED_CONFIG_FILES = (
    "__init__.py",
    "assembly.py",
    "models.py",
    "state.py",
    "validation.py",
)

_REQUIRED_TEST_ROOT_PATHS = ("README.md", "__init__.py")

_REQUIRED_PACKAGE_TEST_PATHS = (
    "__init__.py",
    "conftest.py",
    "e2e/__init__.py",
    "integration/__init__.py",
    "property_based/__init__.py",
    "property_based/internal/__init__.py",
    "property_based/public_contract/__init__.py",
    "support/__init__.py",
    "unit/__init__.py",
)

_REQUIRED_TEMPLATE_TEST_PATHS = (
    "e2e/public_boundary/__init__.py",
    "e2e/public_boundary/test_public_config_pipeline.py",
    "integration/test_config_lifecycle.py",
    "property_based/public_contract/test_config_contract.py",
    "unit/test_public_package.py",
)

_PACKAGE_DOCS = (
    "README.md",
    "architecture/README.md",
    "architecture/concepts/README.md",
    "architecture/concepts/public-boundary-and-errors.md",
    "architecture/flows/README.md",
    "architecture/system.md",
    "dependencies.md",
    "usage.md",
    "verification/README.md",
    "verification/e2e/README.md",
    "verification/public-boundary-and-errors.md",
    "verification/workbench.md",
)


@dataclass(frozen=True, slots=True)
class Violation:
    """One deterministic policy violation."""

    path: Path
    message: str
    line: int | None = None

    def render(self, root: Path) -> str:
        """Render this violation as a stable diagnostic line."""
        try:
            display = self.path.relative_to(root)
        except ValueError:
            display = self.path
        suffix = f":{self.line}" if self.line else ""
        return f"{display}{suffix}: {self.message}"


@dataclass(frozen=True, slots=True)
class ProjectPolicyConfig:
    """Policy-facing Ternforge project metadata."""

    primary_package: str
    package_names: tuple[str, ...]
    public_namespace_packages: tuple[str, ...]


def _table(value: object) -> dict[str, object]:
    """Return a mapping value or an empty table."""
    return value if isinstance(value, dict) else {}


def _normalize_start(start: Path | None) -> Path:
    """Return the resolved starting path for project discovery."""
    return (start or Path.cwd()).expanduser().resolve()


def _find_pyproject(start: Path | None = None) -> Path:
    """Find the nearest pyproject.toml above a starting path."""
    candidate = _normalize_start(start)
    if candidate.is_file():
        candidate = candidate.parent
    for root in (candidate, *candidate.parents):
        path = root / "pyproject.toml"
        if path.is_file():
            return path
    raise FileNotFoundError(f"Could not find pyproject.toml above {candidate}.")


def _read_toml(path: Path) -> dict[str, object]:
    """Read and validate one TOML document as a table."""
    with path.open("rb") as stream:
        value = tomllib.load(stream)
    if not isinstance(value, dict):
        raise TypeError("pyproject.toml root must be a table")
    return value


def _string_tuple(
    value: object, *, field: str, required: bool = False
) -> tuple[str, ...]:
    """Return one validated tuple of unique manifest strings."""
    if value is None and not required:
        return ()
    if not isinstance(value, list) or not value:
        raise TypeError(f"[tool.{_TOOL_TABLE}].{field} must be a non-empty string list")
    values = (_validated_string_item(item, field=field) for item in value)
    return tuple(dict.fromkeys(values))


def _validated_string_item(item: object, *, field: str) -> str:
    """Return one normalized manifest string item."""
    if not isinstance(item, str) or not item.strip():
        raise ValueError(
            f"[tool.{_TOOL_TABLE}].{field} items must be non-empty strings"
        )
    return item.strip()


def _project_config(root: Path) -> ProjectPolicyConfig:
    """Load policy-facing Ternforge metadata for one project root."""
    raw = _read_toml(root / "pyproject.toml")
    tooling = _table(_table(raw.get("tool")).get(_TOOL_TABLE))
    if not tooling:
        raise TypeError(f"pyproject.toml must define [tool.{_TOOL_TABLE}]")
    primary = tooling.get("primary_package")
    if not isinstance(primary, str) or not primary.strip():
        raise ValueError(
            f"[tool.{_TOOL_TABLE}].primary_package must be a non-empty string"
        )
    package_names = _string_tuple(
        tooling.get("package_names"), field="package_names", required=True
    )
    primary = primary.strip()
    if primary not in package_names:
        raise ValueError(
            f"[tool.{_TOOL_TABLE}].primary_package must appear in package_names"
        )
    public_namespaces = _string_tuple(
        tooling.get("public_namespace_packages"),
        field="public_namespace_packages",
    )
    return ProjectPolicyConfig(
        primary_package=primary,
        package_names=package_names,
        public_namespace_packages=public_namespaces,
    )


def discover_project_roots(*, start: Path | None = None) -> tuple[Path, ...]:
    """Return standalone or uv-workspace project roots."""
    pyproject = _find_pyproject(start)
    root = pyproject.parent
    raw = _read_toml(pyproject)
    members = _table(_table(raw.get("tool")).get("uv"))
    workspace = _table(members.get("workspace"))
    values = workspace.get("members")
    if not isinstance(values, list):
        return (root,)
    roots = tuple(
        root / item.strip() for item in values if isinstance(item, str) and item.strip()
    )
    return roots or (root,)
