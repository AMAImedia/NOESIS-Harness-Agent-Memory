# Python 3.14, simulated A/B and sandbox evidence — 2026-08-17

## Evidence matrix

| Gate | Result | Evidence boundary |
|---|---|---|
| Official CPython runtime | **PASS for Linux** | CPython 3.14.7 built from official Python.org source tarball; SHA-256 verified against release page; source SPDX and Sigstore artifacts retained under `runtime/python-3.14.7/src/`. |
| NOESIS Python 3.14 suite | **PASS** | 250 tests passed on CPython 3.14.7 Linux. This is real 3.14 evidence, but not Windows/macOS evidence. |
| Contract benchmark | **PASS** | 10/10 local contract cases passed on CPython 3.14.7. Measures implemented NOESIS primitives only. |
| Simulated external A/B | **PASS as simulation** | `scripts/simulated_external_ab.py` produces `noesis.simulated-external-ab.v1`; NOESIS local contract is observed, Hermes/OpenCode are explicitly `not_run`. No quality ranking is claimed. |
| PyInstaller/Briefcase matrix | **FAIL-CLOSED as intended** | Python 3.14 is accepted, but Linux correctly blocks Windows/macOS target packaging. This proves guard behavior, not native artifact validity. |
| Bubblewrap backend | **PASS for Linux conformance subset** | `sandbox_bwrap.py` uses `--unshare-all`, read-only system mounts, workspace-only write binding, explicit argv and bounded output. Conformance verifies command execution, host project path blocked and network connection blocked. |
| Windows/macOS native evidence | **NOT RUN** | Requires the corresponding operating systems and native Python 3.14 toolchains. |
| External Hermes/OpenCode execution | **NOT RUN** | Requires pinned external runners, exact revisions and same model/provider. |

## Interpretation

The local gates are now materially stronger: NOESIS has a real CPython 3.14 Linux lane and a real Linux Bubblewrap isolation lane. Neither result should be promoted to native Windows/macOS or external competitor evidence. The external A/B report remains protocol-level and fail-closed, with `not_run` for Hermes and OpenCode rather than fabricated metrics.

## Known limitations

Bubblewrap is a Linux backend, not a portable replacement for Windows Job Objects/AppContainer or macOS sandbox profiles. The current backend is an isolation adapter and conformance baseline; production deployment still requires a threat-model review, privilege audit, seccomp/cgroup policy review and native backend equivalents.

Python test output includes non-failing `ResourceWarning` messages from existing SQLite lifecycle code. They do not fail the suite, but they remain a reliability-hardening backlog item and should be resolved before a final release claim.

## References

[1]: https://www.python.org/downloads/release/python-3147/ "Python 3.14.7 official release page"
[2]: https://github.com/containers/bubblewrap "Bubblewrap project"
[3]: https://github.com/NousResearch/hermes-agent "Hermes Agent repository"
[4]: https://opencode.ai/docs/ "OpenCode official documentation"
