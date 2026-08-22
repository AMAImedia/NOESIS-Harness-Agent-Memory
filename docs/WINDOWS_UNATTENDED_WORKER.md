# Windows Unattended NOESIS Worker

The Windows deployment branch contains a stdlib-only unattended worker for the local-first NOESIS Harness. The worker is launched by the `NOESIS-Harness-AutoLoop` Scheduled Task under the Windows `SYSTEM` service account at highest available run level.

## Runtime contract

The worker executes one bounded validation cycle, writes an atomic JSON state record under `.noesis_autoloop/state.json`, appends execution evidence to `.noesis_autoloop/worker.log`, and then sleeps before the next cycle. A filesystem lock prevents overlapping workers. A stale lock is recoverable when its recorded process no longer exists. The default Windows profile runs the verified platform-neutral smoke suite with Python 3.11; Linux retains the full discovery profile.

The task uses an AtStartup trigger plus a fifteen-minute recovery trigger and ignores overlapping instances. It has a bounded restart policy of ten attempts with a two-minute restart interval. The task does not modify the pre-existing `NOESIS_TrainWatchdog` or `NOESIS-YT-*` tasks.

## Safety boundary

The worker validates and records local project state. It does not silently invent code changes, invoke a model, publish a release, or claim external benchmark results. Actual autonomous coding requires an explicitly configured local model command or an approved API-backed command supplied through `NOESIS_AUTOLOOP_COMMAND`; arbitrary commands are not enabled by default. Native Windows packaging, macOS behavior, and external A/B remain separate evidence lanes.

## Live verification

The installed task was verified on the connected Windows host with `RunLevel=Highest`, `User=SYSTEM`, a passing smoke cycle of `73` tests, an advancing heartbeat, and an active lock while the long-lived worker was running. The deployment branch is `windows-autoloop`; the installer and worker changes are synchronized to GitHub.
