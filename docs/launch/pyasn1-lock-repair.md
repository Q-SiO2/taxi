# Runtime lock advisory repair — 1 November 2026

The signed-out acknowledgement candidate `f5be5ff` started CI 274
(`41340668670`). Its backend job (`124949775104`) passed hash-locked install,
then failed the runtime-lock audit at step 7. The audit reported four advisories
for `pyasn1 0.6.4`: `CVE-2026-119194`, `CVE-2026-119195`,
`CVE-2026-119196` and `CVE-2026-119197`, each with `0.6.5` as the fix.
Later backend tests/build/scan steps were skipped. Keep this failed run as
evidence even if its other jobs succeed.

The successor changes only the mirrored `pyasn1` entries in the runtime and
development locks to `0.6.5`. Both SHA256 distribution hashes come from the
[official PyPI metadata](https://pypi.org/pypi/pyasn1/0.6.5/json); neither file
is yanked. The pinned `pyasn1-modules 0.4.2` requires `pyasn1>=0.6.1,<0.7.0`.
A hash-checked wheel download and both separate local lock audits pass with
no known vulnerabilities. The unchanged supplemental Linux lock needs its
combined hash-locked installation and audit in a fresh Linux CI run.

No application source, schema, API contract or deployment configuration is
changed by this lock repair. Physical, signed, provider, hosted, operator,
pilot and public acceptance remain separate.
