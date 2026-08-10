"""Verify manifest loading through the complete public policy path."""

from __future__ import annotations

from pathlib import Path

import py_lib_policy as policy
from tests.py_lib_policy.support.project import _valid_project


def test_project_manifest_reaches_policy_checks(tmp_path: Path) -> None:
    _valid_project(tmp_path, package="policy_target", distribution="policy-target")

    assert policy.check(start=tmp_path) == ()
