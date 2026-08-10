# Public boundary and errors

Supported Python callers import `check`, `ProjectPolicyConfig`, and `Violation` from `py_lib_policy`; `main` remains available for the installed CLI boundary. Invalid repository state is returned as deterministic `Violation` values instead of a second error-reporting path.
