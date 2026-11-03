# R2 remote CI and first-city continuation — 23 October 2026

The source baseline is published as [draft PR #74](https://github.com/Q-SiO2/taxi/pull/74)
against `codex/gap-001-release-baseline`, without merging or deploying it. The
first candidate remains `45c491a4615d466c74c4bb0ca46fd6d55488ad7f`.
[Initial run identities](r2-ci-initial-runs-20261023.json) bind the actual push/PR
runs to that source. The [local checkpoint](r2-candidate.md) remains historical
evidence for its captured files and tests; its local-only status is superseded
by this publication checkpoint, not retroactively rewritten.

Successor **`7d757a69a17fa126caad33c3eb7f4d510c8cf981`** contains the 17 reviewed
corrective inputs and owner-contract updates. It is pushed to the same draft PR.
The [successor run record](r2-corrective-ci-20261023.json) identifies actual push
run 217 (`39989226056`) and PR run 218 (`39989234575`), both observed in progress.
The original checkout HEAD/index remain preserved. These are live job identities,
not passing CI or promotion evidence. Re-observe those same runs before restarting
anything or claiming a terminal outcome.

## Observed initial CI

### Successor terminal observation

[Terminal PR-job evidence](r2-ci-terminal-20261023.json) now confirms that candidate
`7d757a69a17fa126caad33c3eb7f4d510c8cf981` passed backend, mobile, web,
documentation/provenance, wrapper integrity and iOS shared compilation plus both
unsigned iOS simulator application builds. Dependency review was **cancelled**;
the incomplete dependency comparison still prevents an all-green CI claim.
These results precede the membership implementation and cannot accept its source.
No signing, physical iOS acceptance, staging deployment or public promotion follows
from these job results.

- Android/shared and web jobs passed; Gradle wrapper integrity passed. The push
  job also generated and submitted the Gradle dependency graph.
- The documentation/provenance job failed while importing a Windows-only routing
  test on Linux: module-level `import yaml` required an undeclared dependency even
  though the Windows tests themselves are intentionally platform-gated.
- The backend audit rejected `certifi==2026.7.22` for
  `PYSEC-2026-4320` / `GHSA-6q48-6c7w-9gw2`.
- The Mac runner found an unresolved `timeIntervalSince1970` extension in
  `IosCurrentLocationRequester.kt`; iOS compilation therefore did not pass.
- Dependency review exhausted its job time while GitHub reported base/head
  snapshot counts of 1/0. Submission's success is not proof of a complete
  dependency comparison. This remains unresolved; the gate is not weakened.

The failed jobs and cancelled dependency-review observation remain part of the
record. They must not be replaced by the local alpha build results.

## Corrections and local checks

The [correction evidence](r2-ci-corrections-20261023.json) records:

1. Import PyYAML only inside the Windows test that uses it. All **270 infrastructure
   tests pass** locally, including all 11 routing launcher tests. Importing the
   module under `python -I -S` with no PyYAML also succeeds. No test or release
   assertion was removed.
2. Regenerate both hashed locks with `certifi==2026.10.19`; verify that it is the
   only package-version change and retain the hashed development `pip` pin.
   Both final lock audits pass. The local backend installs only that hash-verified
   patch, loads its SSL context and performs a verified HTTPS request to PyPI;
   both release artifact hashes match PyPI's metadata. The
   [reviewed advisory](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) identifies
   the patched release. Existing staging images have not been patched by changing
   the source locks.
3. Import the existing Foundation time extension explicitly on iOS. Verification
   requires the successor Mac CI run; no local Windows iOS-build claim is made.

The corrective candidate must receive fresh immutable CI. Passing initial
Android/web jobs retain their own candidate identity; they do not accept a later
commit automatically. The full goal, R2 and T0 acceptance remain open.

## Owner decisions incorporated during this packet

The [R1 contract](r1-decisions.md) now records **Fès, union operation, union-member
drivers only, normal passenger registration**, and available Android hardware /
Google Play accounts. Product, driver and operations contracts are updated.
Legal identity/authorization and operating rules remain unconfirmed, not rejected
or assumed. iPhone, Mac and Apple Developer resources remain to be arranged.

Source inspection of the preceding candidate found that cooperative memberships were independently
reported without a dispatch eligibility gate. Implement and test the selected
union rule across availability, allocation and acceptance for every enabled
service, including withdrawal after going online. Preserve accepted-trip safety,
completion and financial records. Driver approval and a self-entered membership
number cannot grant membership. No Fès production city, real roster or participant
account has been created by these documentation decisions.

## Continuation

Observe the successor CI head/runs and repair actual failures. Investigate the
missing dependency-review head snapshot without bypassing the security gate.
[The membership checkpoint](union-membership.md) now records that enforcement
slice against the existing operator/member authorities. Its successor source
needs fresh immutable CI, staff/configuration UX and deliberate staging rollout.
Staging trust-bundle rollout also needs its own exact
artifact/deployment evidence; do not replay the previous credential/MFA recovery.
Production, participant enrollment, money, signing and public activation gates
remain unchanged.
