from __future__ import annotations

from pathlib import Path

import pytest

import py_lib_policy as policy
from tests.py_lib_policy.support.project import _messages, _valid_project, _write


def test_valid_nondefault_distribution_and_package(tmp_path: Path) -> None:
    _valid_project(tmp_path, package="actual_pkg", distribution="different-name")
    assert policy.check(start=tmp_path) == ()


def test_old_tool_table_is_rejected(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    path = tmp_path / "pyproject.toml"
    path.write_text(
        path.read_text().replace("[tool.ternforge]", "[tool.py_lib_" + "starter]"),
        encoding="utf-8",
    )
    assert any("[tool.ternforge]" in message for message in _messages(tmp_path))


def test_missing_managed_project_file_is_reported(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    (tmp_path / ".pre-commit-config.yaml").unlink()
    assert "required Ternforge managed project file is missing" in _messages(tmp_path)


def test_missing_source_and_test_paths_are_reported(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    (tmp_path / "src/sample_lib/_api/config.py").unlink()
    (tmp_path / "tests/sample_lib/unit/__init__.py").unlink()
    messages = _messages(tmp_path)
    assert "required Ternforge package path is missing" in messages
    assert "required Ternforge test path is missing" in messages


def test_console_script_must_use_existing_api_facade_function(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    path = tmp_path / "pyproject.toml"
    path.write_text(
        path.read_text()
        + '\n[project.scripts]\nsample = "sample_lib._internal.cli:main"\n',
        encoding="utf-8",
    )
    assert any(
        "project scripts must target" in message for message in _messages(tmp_path)
    )
    path.write_text(
        path.read_text().replace(
            "sample_lib._internal.cli:main", "sample_lib._api.cli:missing"
        ),
        encoding="utf-8",
    )
    _write(tmp_path / "src/sample_lib/_api/cli.py", "def present():\n    return 0\n")
    assert any(
        "target function is missing" in message for message in _messages(tmp_path)
    )


def test_root_initializer_rejects_private_import(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(
        tmp_path / "src/sample_lib/__init__.py",
        "from sample_lib._internal import SampleConfig\n",
    )
    assert "root __init__.py may contain only declaration/facade imports" in _messages(
        tmp_path
    )


def test_root_initializer_accepts_version_fallback(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(
        tmp_path / "src/sample_lib/__init__.py",
        (
            "from importlib.metadata import PackageNotFoundError, version\n"
            "try:\n"
            '    __version__ = version("sample-lib")\n'
            "except PackageNotFoundError:\n"
            '    __version__ = "0.0.0+local"\n'
        ),
    )
    assert policy.check(start=tmp_path) == ()


@pytest.mark.parametrize(
    ("relative", "source", "message"),
    [
        ("_api/__init__.py", "VALUE = 1\n", "`_api/__init__.py` must stay empty"),
        (
            "_api/config.py",
            "def build():\n    pass\n",
            "`_api/config.py` must contain imports only",
        ),
        (
            "_api/defaults.py",
            "def build():\n    pass\n",
            "`_api/defaults.py` must contain constants only",
        ),
        (
            "_api/errors.py",
            "class Value:\n    pass\n",
            "`_api/errors.py` must contain public exception classes only",
        ),
        (
            "_api/types.py",
            "def runtime():\n    pass\n",
            "`_api/types.py` must contain public type declarations only",
        ),
    ],
)
def test_declaration_module_shapes(
    tmp_path: Path, relative: str, source: str, message: str
) -> None:
    _valid_project(tmp_path)
    _write(tmp_path / "src/sample_lib" / relative, source)
    assert any(message in item for item in _messages(tmp_path))


def test_product_api_module_must_define_facade(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(
        tmp_path / "src/sample_lib/_api/product.py",
        "from sample_lib._internal import SampleConfig\n",
    )
    assert (
        "product `_api` modules must define facades, not re-export wrappers"
        in _messages(tmp_path)
    )


def test_all_is_allowed_only_in_public_root(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(
        tmp_path / "src/sample_lib/_internal/config/__init__.py",
        '__all__ = ["SampleConfig"]\n',
    )
    assert "`__all__` must be declared only in root package" in _messages(tmp_path)


def test_private_implementation_must_use_subpackages(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(tmp_path / "src/sample_lib/_internal/service.py", "VALUE = 1\n")
    assert (
        "private implementation modules must live in `_internal` subpackages"
        in _messages(tmp_path)
    )


def test_public_root_children_must_be_declared_or_private(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(tmp_path / "src/sample_lib/public_module.py", "VALUE = 1\n")
    _write(tmp_path / "src/sample_lib/public_package/__init__.py")
    messages = _messages(tmp_path)
    assert (
        "public-looking root module must live under `_api` or `_internal`" in messages
    )
    assert (
        "public-looking root package must be declared or moved under `_api`/`_internal`"
        in messages
    )


def test_declared_public_namespace_is_allowed(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    path = tmp_path / "pyproject.toml"
    path.write_text(
        path.read_text().replace(
            'library_lane = "standard-lib"',
            'library_lane = "standard-lib"\npublic_namespace_packages = [ "models" ]',
        ),
        encoding="utf-8",
    )
    _write(tmp_path / "src/sample_lib/models/__init__.py")
    assert policy.check(start=tmp_path) == ()


def test_literal_dynamic_private_import_is_rejected(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(
        tmp_path / "src/sample_lib/_api/product.py",
        (
            "import importlib\n"
            "def load():\n"
            '    return importlib.import_module("sample_lib._internal.config")\n'
        ),
    )
    assert "string-based dynamic import of `_internal` is forbidden" in _messages(
        tmp_path
    )


def test_generic_static_import_relationship_is_left_to_import_linter(
    tmp_path: Path,
) -> None:
    _valid_project(tmp_path)
    _write(
        tmp_path / "src/sample_lib/_internal/config/state.py",
        "from sample_lib._api.config import SampleConfig\n",
    )
    assert not any(
        "must not import public" in message for message in _messages(tmp_path)
    )


def test_examples_enforce_location_marker_and_private_string_references(
    tmp_path: Path,
) -> None:
    _valid_project(tmp_path)
    _write(tmp_path / "examples/loose.py", "print('loose')\n")
    _write(
        tmp_path / "examples/sample_lib/demo.py",
        'print("sample_lib._internal.config")\n',
    )
    messages = _messages(tmp_path)
    assert "examples must live under `examples/<package>/`" in messages
    assert (
        "runnable examples must start with `# %%` for IPython console use" in messages
    )
    assert "examples must not reference private package modules" in messages


def test_e2e_and_workbench_require_cell_markers(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(tmp_path / "tests/sample_lib/e2e/case.py", "print('case')\n")
    _write(tmp_path / "workbench/sample_lib/probe.py", "print('probe')\n")
    messages = _messages(tmp_path)
    assert (
        "runnable e2e tests must start with `# %%` for IPython console use" in messages
    )
    assert (
        "runnable workbench modules must start with `# %%` for IPython console use"
        in messages
    )


def test_complete_docs_skeleton_is_required(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    (tmp_path / "docs/sample_lib/architecture/concepts/README.md").unlink()
    assert "required Ternforge docs file is missing" in _messages(tmp_path)


def test_configured_e2e_slice_requires_path_and_documentation(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(
        tmp_path / ".copier-answers.yml",
        (
            "e2e_slices:\n"
            "  - name: custom-flow\n"
            "    path: tests/__PACKAGE_NAME__/e2e/custom_flow\n"
        ),
    )
    messages = _messages(tmp_path)
    assert "configured e2e slice directory is missing" in messages
    assert "configured e2e slice documentation is missing" in messages
    (tmp_path / "tests/sample_lib/e2e/custom_flow").mkdir(parents=True)
    _write(
        tmp_path / "docs/sample_lib/verification/e2e/custom-flow.md", "# Custom flow\n"
    )
    assert policy.check(start=tmp_path) == ()


def test_malformed_e2e_slice_config_fails_closed(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(tmp_path / ".copier-answers.yml", "e2e_slices: invalid\n")
    assert any(
        "e2e_slices must be a list" in message for message in _messages(tmp_path)
    )


def test_uv_workspace_members_are_checked(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        (
            "[project]\n"
            'name = "workspace"\n'
            'version = "1.0.0"\n'
            "[tool.uv.workspace]\n"
            'members = [ "packages/one", "packages/two" ]\n'
        ),
    )
    _valid_project(tmp_path / "packages/one", package="one")
    _valid_project(tmp_path / "packages/two", package="two")
    assert policy.check(start=tmp_path) == ()
    (tmp_path / "packages/two/src/two/py.typed").unlink()
    assert "required Ternforge package path is missing" in _messages(tmp_path)
