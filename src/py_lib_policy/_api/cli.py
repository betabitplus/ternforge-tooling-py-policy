"""Installed command facade."""

from __future__ import annotations

from py_lib_policy._internal import main as _main


def main(argv: list[str] | None = None) -> int:
    """Run the policy command-line interface and return its exit status."""
    return _main(argv)
