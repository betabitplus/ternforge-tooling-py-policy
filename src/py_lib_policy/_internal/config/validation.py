"""Validation helpers for Ternforge policy configuration."""

from __future__ import annotations

from py_lib_policy._api.defaults import _TOOL_TABLE


def _table(value: object) -> dict[str, object]:
    """Return a mapping value or an empty table."""
    return value if isinstance(value, dict) else {}


def _string_tuple(
    value: object, *, field: str, required: bool = False
) -> tuple[str, ...]:
    """Return one validated tuple of unique manifest strings."""
    if value is None and not required:
        return ()
    if not isinstance(value, list) or not value:
        msg = f"[tool.{_TOOL_TABLE}].{field} must be a non-empty string list"
        raise TypeError(msg)
    values = (_validated_string_item(item, field=field) for item in value)
    return tuple(dict.fromkeys(values))


def _validated_string_item(item: object, *, field: str) -> str:
    """Return one normalized manifest string item."""
    if not isinstance(item, str) or not item.strip():
        msg = f"[tool.{_TOOL_TABLE}].{field} items must be non-empty strings"
        raise ValueError(msg)
    return item.strip()
