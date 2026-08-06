# Verification

Run the policy tests with:

```bash
uv run pytest tests/py_lib_policy
```

Run the complete repository gate with:

```bash
uv run pre-commit run --all-files --hook-stage pre-push
```

The gate covers types, imports, complexity, security, dependency hygiene, documentation, packaging, and isolated distribution checks.
