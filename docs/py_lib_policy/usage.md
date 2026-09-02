# Usage

Use `py_lib_policy.check(start=path)` from Python or run `py-lib-policy check` from a repository root. A clean repository returns no violations and exits successfully.

## Engineering Experiment capsules

`experiments/` is optional. When present, policy treats it as an isolated filesystem zone rather than a Python package. Durable experiments live under `experiments/<project>/exp_####_<slug>/` and own their Python source, captured notebook, inputs, artifacts, dependency metadata, lockfile, and Python pin.

Policy checks only reusable structural invariants: canonical capsule layout, no loose/shared experiment code, no imports from the parent project or sibling experiments, no reverse product dependency on experiments, no local/workspace/editable dependencies, and no symlinks escaping a capsule. Notebook narrative, execution outputs, stale-result digests, and Sphinx rendering belong to report tooling rather than `py-lib-policy`.

The legacy top-level `workbench/` convention is rejected once a project adopts this policy version.
