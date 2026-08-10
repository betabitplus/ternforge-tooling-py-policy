"""Deterministic policy violation model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Violation:
    """One deterministic policy violation."""

    path: Path
    message: str
    line: int | None = None

    def render(self, root: Path) -> str:
        """Render this violation as a stable diagnostic line."""
        try:
            display = self.path.relative_to(root)
        except ValueError:
            display = self.path
        suffix = f":{self.line}" if self.line else ""
        return f"{display}{suffix}: {self.message}"
