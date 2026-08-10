"""Policy-facing Ternforge project metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectPolicyConfig:
    """Validated project metadata consumed by policy checks."""

    primary_package: str
    package_names: tuple[str, ...]
    public_namespace_packages: tuple[str, ...]
