# Development lock security repair — 29 October 2026

The source candidate at `2ff36933cc16d7babfc92f658325e359b86f91fc`
started CI run 262 (`40791030152`). Its backend job (`123176005627`)
passed hash-locked installation and the runtime-lock audit, then failed the
development/Linux lock audit at step 8. The audit reported `msgpack 1.2.1`,
`CVE-2026-114613`, with `1.2.3` as a fix. Later backend steps were skipped;
this run is not backend acceptance, regardless of its other jobs' outcomes.

The successor changes only the transitive `msgpack` development lock entry to
`1.2.3` and replaces its distribution hashes with all 91 SHA256 hashes listed
for that version in the [PyPI release metadata](https://pypi.org/pypi/msgpack/1.2.3/json).
No runtime lock, package constraint, application source, or API contract changes.
The source diff must remain limited to that entry. A local hash-checked Windows
wheel download and `pip-audit --no-deps` against the development lock pass.
The combined development/Linux audit cannot run on the Windows host because
its existing `uvloop` Linux-only hash set does not cover the Windows source
distribution chosen by pip; the CI Linux audit remains the acceptance check.

Retain the failed CI run and its diagnostics. A subsequent immutable source
commit needs a fresh CI run with every required job successful. This source
repair does not advance physical-device, hosted, provider, pilot, or public
release gates.
