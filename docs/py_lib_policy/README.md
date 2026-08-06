# py-lib-policy

`py-lib-policy` validates Ternforge-specific Python repository structure that is not covered by generic lint, type, security, dependency, or packaging tools.

The public interface is `py_lib_policy.check()`. The `py-lib-policy check` console command renders deterministic violations and exits nonzero when a repository breaks the policy.

See [verification](verification/README.md) for the validation workflow.
