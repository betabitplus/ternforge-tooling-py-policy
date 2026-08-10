"""Private implementation exports consumed by public facades."""

from __future__ import annotations

from py_lib_policy._internal.config import ProjectPolicyConfig as ProjectPolicyConfig
from py_lib_policy._internal.policy import (
    Violation as Violation,
    check as check,
    main as main,
)
