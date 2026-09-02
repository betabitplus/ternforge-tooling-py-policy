from __future__ import annotations

from pathlib import Path

import py_lib_policy as policy
from tests.py_lib_policy.support.project import (
    _messages,
    _valid_experiment,
    _valid_project,
    _write,
)


def test_project_without_experiments_is_valid(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    assert policy.check(start=tmp_path) == ()


def test_standalone_experiment_capsule_is_valid(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _valid_experiment(tmp_path)
    assert policy.check(start=tmp_path) == ()


def test_legacy_workbench_is_rejected(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _write(tmp_path / "workbench" / "sample_lib" / "probe.py", "print('probe')\n")
    assert any(
        "legacy `workbench/` is forbidden" in item for item in _messages(tmp_path)
    )


def test_experiment_namespace_must_not_be_a_python_package(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _valid_experiment(tmp_path)
    _write(tmp_path / "experiments" / "__init__.py")
    _write(tmp_path / "experiments" / "sample_lib" / "__init__.py")
    messages = _messages(tmp_path)
    assert "experiments is a filesystem zone, not a shared Python package" in messages
    assert "experiment project namespaces must not be Python packages" in messages


def test_loose_or_shared_experiment_code_is_rejected(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _valid_experiment(tmp_path)
    _write(tmp_path / "experiments" / "sample_lib" / "loose.py", "VALUE = 1\n")
    _write(tmp_path / "experiments" / "sample_lib" / "shared" / "helper.py")
    messages = _messages(tmp_path)
    assert "loose experiment Python must live inside a capsule" in messages
    assert "shared experiment code directories are forbidden" in messages


def test_capsule_requires_canonical_layout(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    capsule = _valid_experiment(tmp_path)
    (capsule / "uv.lock").unlink()
    _write(capsule / "report" / "helper.py", "VALUE = 1\n")
    _write(capsule / "src" / "nested" / "experiment.py", "VALUE = 1\n")
    messages = _messages(tmp_path)
    assert "required experiment capsule file is missing" in messages
    assert "experiment Python source must live under `src/`" in messages
    assert "capsule must expose exactly one canonical `src/experiment.py`" in messages


def test_python_is_forbidden_in_inputs_and_artifacts(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    capsule = _valid_experiment(tmp_path)
    _write(capsule / "inputs" / "prepare.py", "VALUE = 1\n")
    _write(capsule / "artifacts" / "replay.py", "VALUE = 1\n")
    messages = _messages(tmp_path)
    assert messages.count("experiment Python source must live under `src/`") == 2


def test_nested_capsule_is_rejected(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    capsule = _valid_experiment(tmp_path)
    (capsule / "src" / "exp_0002_nested").mkdir()
    assert "nested experiment capsules are forbidden" in _messages(tmp_path)


def test_capsule_imports_parent_or_sibling_namespaces_are_rejected(
    tmp_path: Path,
) -> None:
    _valid_project(tmp_path)
    capsule = _valid_experiment(tmp_path)
    _write(
        capsule / "src" / "probe.py",
        (
            "import sample_lib\n"
            "from experiments.other import probe\n"
            "from tests import support\n"
        ),
    )
    messages = _messages(tmp_path)
    assert (
        messages.count(
            "experiment must not import parent/sibling project code: sample_lib"
        )
        == 1
    )
    assert any("experiments.other" in item for item in messages)
    assert any("tests" in item and "parent/sibling" in item for item in messages)


def test_product_tests_and_examples_must_not_import_experiments(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    _valid_experiment(tmp_path)
    _write(
        tmp_path / "src" / "sample_lib" / "_internal" / "config" / "state.py",
        "import experiments.sample_lib\n",
    )
    assert "product/tests/examples must not import experiments" in _messages(tmp_path)


def test_capsule_rejects_parent_and_local_dependencies(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    capsule = _valid_experiment(tmp_path)
    (capsule / "pyproject.toml").write_text(
        """[project]
name = "exp_0001_probe"
version = "0.0.0"
dependencies = [ "sample-lib", "helper @ ../helper" ]

[tool.uv]
sources.helper = { path = "../helper", editable = true }
""",
        encoding="utf-8",
    )
    messages = _messages(tmp_path)
    assert any("parent project package: sample-lib" in item for item in messages)
    assert any("must not use a local path" in item for item in messages)
    assert any("path/workspace/editable coupling" in item for item in messages)


def test_capsule_rejects_uv_workspace_membership(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    capsule = _valid_experiment(tmp_path)
    with (capsule / "pyproject.toml").open("a", encoding="utf-8") as stream:
        stream.write('\n[tool.uv.workspace]\nmembers = [ "packages/*" ]\n')
    assert "experiment must be a standalone uv project" in _messages(tmp_path)


def test_capsule_allows_immutable_git_dependency(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    capsule = _valid_experiment(tmp_path)
    with (capsule / "pyproject.toml").open("a", encoding="utf-8") as stream:
        stream.write(
            "\n[tool.uv.sources]\n"
            'helper = { git = "https://example.test/helper.git", '
            'tag = "v1.2.3" }\n'
        )
    assert policy.check(start=tmp_path) == ()


def test_capsule_symlink_must_not_escape(tmp_path: Path) -> None:
    _valid_project(tmp_path)
    capsule = _valid_experiment(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    link = capsule / "inputs" / "outside.txt"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside)
    assert "experiment symlink must not escape capsule" in _messages(tmp_path)
