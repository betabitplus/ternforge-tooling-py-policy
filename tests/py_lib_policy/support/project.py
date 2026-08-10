"""Repository fixtures shared by policy tests."""

from __future__ import annotations

from pathlib import Path

import py_lib_policy as policy

PACKAGE_DOCS = (
    "README.md",
    "architecture/README.md",
    "architecture/concepts/README.md",
    "architecture/concepts/public-boundary-and-errors.md",
    "architecture/flows/README.md",
    "architecture/system.md",
    "dependencies.md",
    "usage.md",
    "verification/README.md",
    "verification/e2e/README.md",
    "verification/public-boundary-and-errors.md",
    "verification/workbench.md",
)


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _valid_project(
    root: Path, *, package: str = "sample_lib", distribution: str = "sample-lib"
) -> None:
    _write(
        root / "pyproject.toml",
        "\n".join(
            [
                "[project]",
                f'name = "{distribution}"',
                'version = "1.2.3"',
                "",
                "[tool.ternforge]",
                f'primary_package = "{package}"',
                f'package_names = [ "{package}" ]',
                f'env_prefix = "{package.upper()}"',
                'library_lane = "standard-lib"',
                "",
            ]
        ),
    )
    package_root = root / "src" / package
    _write(
        package_root / "__init__.py",
        "\n".join(
            [
                '"""Public package."""',
                "from __future__ import annotations",
                f"from {package}._api.config import SampleConfig",
                '__all__ = ["SampleConfig"]',
                "",
            ]
        ),
    )
    _write(package_root / "py.typed")
    _write(package_root / "_api" / "__init__.py", '"""Public declarations."""\n')
    _write(
        package_root / "_api" / "config.py",
        f"from {package}._internal import SampleConfig\n",
    )
    _write(package_root / "_api" / "defaults.py", "DEFAULT_LEVEL = 10\n")
    _write(
        package_root / "_api" / "errors.py", "class SampleError(Exception):\n    pass\n"
    )
    _write(
        package_root / "_api" / "types.py",
        (
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class SampleType:\n"
            "    value: str\n"
        ),
    )
    _write(
        package_root / "_internal" / "__init__.py",
        f"from {package}._internal.config import SampleConfig\n",
    )
    _write(
        package_root / "_internal" / "config" / "__init__.py",
        "from .models import SampleConfig\n",
    )
    _write(
        package_root / "_internal" / "config" / "assembly.py",
        "def build_config():\n    return None\n",
    )
    _write(
        package_root / "_internal" / "config" / "models.py",
        "class SampleConfig:\n    pass\n",
    )
    _write(
        package_root / "_internal" / "config" / "state.py",
        "def get_config():\n    return None\n",
    )
    _write(
        package_root / "_internal" / "config" / "validation.py",
        "def validate():\n    return None\n",
    )

    tests = root / "tests"
    _write(tests / "README.md", "# Tests\n")
    _write(tests / "__init__.py")
    package_tests = tests / package
    for relative in (
        "__init__.py",
        "conftest.py",
        "e2e/__init__.py",
        "e2e/public_boundary/__init__.py",
        "e2e/public_boundary/test_public_config_pipeline.py",
        "integration/__init__.py",
        "integration/test_config_lifecycle.py",
        "property_based/__init__.py",
        "property_based/internal/__init__.py",
        "property_based/public_contract/__init__.py",
        "property_based/public_contract/test_config_contract.py",
        "support/__init__.py",
        "unit/__init__.py",
        "unit/test_public_package.py",
    ):
        text = (
            "# %%\n"
            if relative.endswith(".py")
            and "/e2e/" in f"/{relative}"
            and not relative.endswith("__init__.py")
            else ""
        )
        _write(package_tests / relative, text)

    _write(root / "docs" / "README.md", "# Docs\n")
    for relative in PACKAGE_DOCS:
        _write(root / "docs" / package / relative, "# Doc\n")
    _write(root / "examples" / "__init__.py")
    _write(root / "examples" / package / "__init__.py")
    _write(root / "examples" / package / "demo.py", "# %%\nprint('demo')\n")
    _write(root / "workbench" / "__init__.py")
    _write(root / "workbench" / package / "__init__.py")
    _write(root / "workbench" / package / "probe.py", "# %%\nprint('probe')\n")
    for relative in (
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".pre-commit-config.yaml",
        ".release-please-manifest.json",
        "release-please-config.json",
        "renovate.json5",
    ):
        _write(root / relative)
    _write(root / ".copier-answers.yml", "e2e_slices: []\n")


def _messages(root: Path) -> list[str]:
    return [item.message for item in policy.check(start=root)]
