"""Declarative Ternforge policy constants."""

from __future__ import annotations

_TOOL_TABLE = "ternforge"
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

_REQUIRED_MANAGED_PROJECT_FILES = (
    ".copier-answers.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    ".pre-commit-config.yaml",
    ".release-please-manifest.json",
    "pyproject.toml",
    "release-please-config.json",
    "renovate.json5",
)

_REQUIRED_TEST_ROOT_PATHS = ("README.md", "__init__.py")

_REQUIRED_PACKAGE_TEST_PATHS = (
    "__init__.py",
    "conftest.py",
    "integration/__init__.py",
    "property_based/__init__.py",
    "property_based/internal/__init__.py",
    "property_based/public_contract/__init__.py",
    "support/__init__.py",
    "unit/__init__.py",
)

_PACKAGE_DOCS = (
    "README.md",
    "architecture/README.md",
    "architecture/concepts/README.md",
    "architecture/concepts/public-boundary-and-errors.md",
    "architecture/flows/README.md",
    "architecture/system.md",
    "dependencies.md",
    "verification/README.md",
    "verification/public-boundary-and-errors.md",
    "verification/workbench.md",
)
