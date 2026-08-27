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
