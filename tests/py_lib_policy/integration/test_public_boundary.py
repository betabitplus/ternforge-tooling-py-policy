"""Exercise the installed public policy and CLI boundaries."""

from __future__ import annotations

from pathlib import Path

import py_lib_policy as policy
from tests.py_lib_policy.support.project import _valid_project


def test_public_check_and_cli_accept_valid_project(tmp_path: Path) -> None:
    _valid_project(tmp_path)

    assert policy.check(start=tmp_path) == ()
    assert policy.main([str(tmp_path)]) == 0
