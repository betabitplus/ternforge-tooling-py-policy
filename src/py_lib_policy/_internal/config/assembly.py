"""Load policy configuration from one Ternforge project."""

from __future__ import annotations

import tomllib
from pathlib import Path

from py_lib_policy._api.defaults import _TOOL_TABLE
from py_lib_policy._internal.config.models import ProjectPolicyConfig
from py_lib_policy._internal.config.validation import _string_tuple, _table


def _read_toml(path: Path) -> dict[str, object]:
    """Read one TOML document."""
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _project_config(root: Path) -> ProjectPolicyConfig:
    """Load policy-facing Ternforge metadata for one project root."""
    raw = _read_toml(root / "pyproject.toml")
    tooling = _table(_table(raw.get("tool")).get(_TOOL_TABLE))
    if not tooling:
        msg = f"pyproject.toml must define [tool.{_TOOL_TABLE}]"
        raise TypeError(msg)
    primary = tooling.get("primary_package")
    if not isinstance(primary, str) or not primary.strip():
        msg = f"[tool.{_TOOL_TABLE}].primary_package must be a non-empty string"
        raise ValueError(msg)
    package_names = _string_tuple(
        tooling.get("package_names"), field="package_names", required=True
    )
    primary = primary.strip()
    if primary not in package_names:
        msg = f"[tool.{_TOOL_TABLE}].primary_package must appear in package_names"
        raise ValueError(msg)
    public_namespaces = _string_tuple(
        tooling.get("public_namespace_packages"),
        field="public_namespace_packages",
    )
    return ProjectPolicyConfig(
        primary_package=primary,
        package_names=package_names,
        public_namespace_packages=public_namespaces,
    )
