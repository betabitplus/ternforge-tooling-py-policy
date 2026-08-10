"""Configuration loading and project discovery internals."""

from __future__ import annotations

from py_lib_policy._internal.config.assembly import _project_config as _project_config
from py_lib_policy._internal.config.models import (
    ProjectPolicyConfig as ProjectPolicyConfig,
)
from py_lib_policy._internal.config.state import (
    _normalize_start as _normalize_start,
    discover_project_roots as discover_project_roots,
)
