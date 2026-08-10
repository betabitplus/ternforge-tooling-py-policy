"""Check invalid public manifest values across whitespace forms."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, strategies as st

import py_lib_policy as policy
from tests.py_lib_policy.support.project import _valid_project


@given(st.sampled_from(["", " ", "\t", "  \t  "]))
def test_primary_package_rejects_blank_values(value: str) -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        _valid_project(root)
        pyproject = root / "pyproject.toml"
        pyproject.write_text(
            pyproject.read_text(encoding="utf-8").replace(
                'primary_package = "sample_lib"', f'primary_package = "{value}"'
            ),
            encoding="utf-8",
        )

        violations = policy.check(start=root)

        assert len(violations) == 1
        assert "primary_package must be a non-empty string" in violations[0].message
