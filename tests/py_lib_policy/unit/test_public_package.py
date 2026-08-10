"""Pin the supported top-level Python API."""

from __future__ import annotations

import py_lib_policy as policy


def test_public_package_exports_stay_stable() -> None:
    assert policy.__all__ == ["ProjectPolicyConfig", "Violation", "check", "main"]
    assert callable(policy.check)
    assert callable(policy.main)
