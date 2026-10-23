# Development dependency correction — 23 October 2026

Status: **scoped local correction verified; successor CI pending**. R2 continues
the [session/release packet](session-recovery.md), with the full
[R0–R12 objective](../real-world-launch.md) unchanged.

## Observed failure and correction

[CI run 226](https://github.com/Q-SiO2/taxi/actions/runs/40040360195), source
`aeff4a25d1d07ab8f6762fad9826af90cfb5708d`, passed its runtime Python lock audit
but rejected the development/Linux-lock audit before backend tests. It reported
`filelock 3.32.2` against CVE-2026-112940, CVE-2026-112913 and CVE-2026-112907,
all with fixed version 4.2.1. Do not report this backend job or overall CI as passing.

`filelock` is used by `CacheControl[filecache]`, which supports `pip-audit`.
It is absent from the application runtime lock. The scoped regeneration changes
only this transitive development pin to **4.2.4** and its wheel/sdist hashes.
No application, Linux-only runtime dependency, schema, authorization or CI gate
changes. No vulnerability exception or ignored finding is introduced.

The [maintainer advisory](https://github.com/tox-dev/filelock/security/advisories/GHSA-v4x8-3wr5-3wq8)
identifies 4.2.1 as the patched boundary for the SQLite-lock finding. The
[maintainer changelog](https://raw.githubusercontent.com/tox-dev/filelock/4.2.4/docs/changelog.rst)
records subsequent 4.2 patch fixes. The
[PyPI metadata](https://pypi.org/pypi/filelock/4.2.4/json) supplies the two hashes,
no additional runtime requirements, and Python >=3.11 support, compatible with
the project's >=3.12 requirement. Metadata compatibility is not a Linux test run.

## Verification and retained limits

- `pip-compile` using the existing isolated tool environment regenerates the
  lock; comparison confirms only `filelock` changes. Hash-required installation
  installs only that package, and `pip check` reports no broken requirements.
- Native Windows/Python 3.14 `pip-audit --no-deps -r requirements-dev.lock`
  completes with no known vulnerabilities. Actual installed CacheControl file
  cache checks pass read/write, replacement, concurrent complete writes and deletion.
- The first compile attempt used the application environment's incompatible
  pip-tools/pip pair and failed before editing the lock. The existing tool
  environment (pip 25.3) performs the successful regeneration; no application
  pip downgrade or tool-compatibility bypass is applied.
- A local combined development/Linux audit failed because Windows selects an
  unapproved `uvloop` source archive instead of the deliberately locked Linux
  wheels. Its hashes were not relaxed. Fresh native Linux CI must perform the
  full existing hash install, combined audit and backend suite.
- The unchanged application web inputs retain their
  [terminal production/package/partial-Chrome evidence](session-release-terminal-20261023.json).
  Do not rebuild unchanged web source merely to bind a different development lock.

The [machine-readable correction record](dependency-refresh-verification-20261023.json)
retains the package comparison, release hashes, audit/consumer results and source
failure identity. Fresh immutable CI and any deliberate staging rollout remain
separate. Existing Trial-only spending, protected volumes and staff/credential
boundaries remain in force.
