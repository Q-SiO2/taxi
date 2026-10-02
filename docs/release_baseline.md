# TaxiMobile — Release Baseline Record

## Purpose

This record defines the reviewed source scope and verification boundary for the
first GAP-001 candidate baseline. It is release provenance, not authorization to
deploy, start a pilot, accept a testing phase, or publish a store artifact.

**Candidate label:** `gap-001-baseline-20260910`

**Recorded:** 2026-09-10

**Migration head:** `20260908_0052`

The immutable source identity is the Git commit that contains this file. Do not
copy a commit hash into this document: the CI-generated release-evidence record
binds the checked-out commit and tree without creating a self-referential commit.

## Included source scope

This candidate consolidates the release-evidence and phased-test work that was
previously present only in the working tree:

* T2's bounded 20-persona/60-test catalog and outbound-network denial guard.
* T3 JUnit, secret-free database metadata, isolated logical restore and combined
  evidence generation.
* T4's closed 56-case device/browser/accessibility/lifecycle/crash laboratory
  catalog and its deliberately unexecuted template.
* Android passenger/driver registration-login device-report collection without
  raw serials, credentials, entered values or automatic acceptance claims.
* Deterministic Android and iOS verification manifests that identify both role
  products while marking unsigned/providerless outputs non-distributable.
* Static web compatibility-loader scenarios, packaged JS/Wasm release checks and
  bounded real Chrome/Firefox boot evidence.
* CI controls that retain these records, bind their hashes to exact clean source
  identity and reject removal of limitation or no-acceptance statements.
* Documentation that maps T0 through T10 from simulation to national operation.

No product business rule, database migration, public API contract, pricing rule,
or payment authority is introduced by this candidate.

## Local candidate verification

The following checks passed against the candidate source before this record was
created. Generated records live under ignored build directories and must be
recreated by CI for the immutable commit.

| Gate | Result | Acceptance boundary |
| --- | --- | --- |
| Source credential hygiene | Passed | Local secret files were excluded; this is not an independent secret-history review. |
| Documentation and phase validators | Passed | Structural consistency only; no phase was accepted. |
| Infrastructure script suite | 88 passed | Includes T2/T3/T4 evidence and CI mutation tests. |
| Mobile release-script suite | 36 passed | No physical device or signed distribution acceptance. |
| Static compatibility-loader runtime | 6 scenarios passed | Dependency-free loader behavior, not hosted browser E2E. |
| Shared JVM, Android passenger/driver compile, JS/Wasm browser suites | Gradle build passed | Windows cannot execute iOS simulator tests. |
| Fresh PostGIS backend suite | 992 passed with zero failures/errors/skips | Current-head local system evidence, not capacity or hosted acceptance. |
| T3 database reconciliation | 81 tables restored at migration 0052; temporary target/dump removed | Local logical restore, not managed encrypted backup/PITR acceptance. |
| Packaged browser boot smoke | 4/4 Chrome 152 and 4/4 Firefox 155 scenarios passed with eight screenshots | Safari, authenticated journeys, accessibility, hosted headers and firewalled egress remain open. |
| Backend image high/critical scan | Alpine candidate passed with zero Trivy findings; runtime ran as UID 2000 and imported the API module | Local image only; CI must rebuild and scan the exact clean commit, then a registry must retain its deployment digest. |

The local T3 report confirms all six required evidence kinds, zero residual test
clone databases and revoked temporary `CREATEDB` authority. It deliberately keeps
`phase_accepted=false` and `deployment_accepted=false`.

## Current immutable remote evidence

The latest complete source candidate with passing immutable automation is
`17a94df95f310f2e5b0d98eabba60bf83bb3344e`, verified on 2026-10-02 by
[push CI](https://github.com/Q-SiO2/taxi/actions/runs/37026466549) and
[PR CI](https://github.com/Q-SiO2/taxi/actions/runs/37026471915). Both retained
OpenAPI packets were downloaded and reconciled: schema sizes/hashes match the
manifest and backend source binding, which records migration 0052, clean source
and no deployment acceptance. The push binds that branch-head commit; the PR
binds GitHub's test merge `57ec3e5a93e1dffe07302e1182ca8fd96098ede4`.
Both tested trees are `a0db5ac405f37b94036359373a9a5cf63a8cde87`; equal trees do
not make the two commits interchangeable. The subsequent registry-publication
patch requires its own immutable CI and actual main publication evidence.

The preceding Android source candidate is
`cc19776fdc804093bffdfe92023679258a66a023`, verified on 2026-10-02 by
[push CI](https://github.com/Q-SiO2/taxi/actions/runs/37023593864) and
[PR CI](https://github.com/Q-SiO2/taxi/actions/runs/37023603230). Both include the
Android storage patch and both iOS Release simulator links. They do not accept
real Keystore/disk behavior, native iOS test execution, signed distributions or
deployment. Its source evidence does not certify the later OpenAPI or registry
patches; the OpenAPI candidate has its own passing automation above.

The latest verified server source is
`2d6a68b04eccd793d5d071b8f26bba67568bf63b`, successful on 2026-10-02 in
[push CI](https://github.com/Q-SiO2/taxi/actions/runs/37000510927) and
[PR CI](https://github.com/Q-SiO2/taxi/actions/runs/37000515435). Both include
backend, mobile, web, documentation/security and two iOS Release simulator
application links. Simulator linking is not native iOS test execution or signing.
These runs do not certify the subsequent Android protected-storage patch;
that candidate must acquire its own clean-source evidence. No physical/hosted
acceptance, registry promotion or real-user authorization is inferred.
The earlier run below is retained as dated provenance, not current acceptance.

On 2026-09-28, commit `de69829a649715ad7768756e285fedfde2fa846a`
passed the complete
[push workflow](https://github.com/Q-SiO2/taxi/actions/runs/36430942057) and
[pull-request workflow](https://github.com/Q-SiO2/taxi/actions/runs/36430946742).
The runs covered documentation/provenance, backend/PostGIS, Android/shared,
JavaScript/Wasm/web packaging, wrapper integrity, dependency submission/review,
and both Passenger and Driver iOS Release simulator application links. The iOS
job restored the committed 14-package graph, generated the two-product manifest,
and bound it to clean-source evidence. MapLibre Compose issue 824 still prevents
native iOS test linking, and no native iOS test execution is claimed.

This satisfies the remote-CI item below for that source commit only. It does not
supply independent pull-request approval, signed mobile
distribution artifacts, an immutable registry image digest, or release approval.
Those controls remain necessary before GAP-001 can close.

## Protected promotion and backend image storage — 2026-10-02

The owner explicitly authorized protecting `main`. GitHub readback confirms seven
required GitHub Actions checks (`backend`, `mobile`, `web`, `ios-shared`,
`documentation-and-provenance`, `gradle-wrapper-integrity`, `dependency-review`),
strict up-to-date checks, one independent approval including the latest push,
stale-review dismissal, administrator enforcement and resolved conversations.
Force pushes and deletion are disabled. The push-only dependency-submission job
is not a required PR check. PR 43 is still draft and has no independent approval;
protection does not manufacture review or authorize merging.

Under the owner's delegated no-cost technical setup, backend image storage uses
`ghcr.io/q-sio2/taxi-api`. GitHub currently provides container-image storage and
bandwidth without charge; this is not a perpetual price guarantee or an API,
worker or database host. See [GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages).
The provider-neutral running topology and taxi-owned/driver-choice product remain
unchanged; no commission, tariff or payment policy changes follow from this choice.

Only a successful `main` push may publish. The backend exports its already-built,
scanned Linux/amd64 image and SPDX SBOM; a separate least-privilege package-write
job waits for all seven push verification jobs. It downloads only this run and
attempt's archive, verifies source/run/hash identity before loading Docker,
verifies the loaded image ID, uses the temporary workflow token, and pushes a
commit/run/attempt-specific tag (never `latest`). It pulls the resulting immutable
registry digest and verifies that it is still the scanned image before retaining
provenance. Rebuilding after the scan is forbidden because even the same source
can resolve different upgraded operating-system packages. The PR and feature
branch runs neither export nor publish images.

The transfer archive expires after one day; compact registry provenance and SBOM
are retained for 30 days. Preserve approved release evidence before expiry.
Rerun the whole workflow if the same-run archive expires; a partial publication
rerun uses a different attempt and deliberately cannot borrow another attempt's
archive. The package defaults to private; anonymous pulls require a separately
reviewed visibility/access decision. CI artifacts and unsigned JSON are trusted
through the workflow/run service, not standalone cryptographic attestations.

No registry image or digest is claimed until the reviewed workflow reaches main
and publication succeeds. Mobile signing, actual review, controlled evidence
custody and release approval remain missing. Docker execution/push/pull requires
Linux CI: local Docker was unavailable during this slice. Unit/mutation checks
exercise the protocol but cannot establish successful registry publication.

## Required immutable promotion evidence

### Android packaged identity (2026-10-02)

`TaxiMobile/scripts/generate_android_verification_manifest.py` validates actual
binary-manifest package/version identities with the SDK's `aapt2 dump badging`.
AGP metadata alone is not proof: it could describe a different APK or point
outside the expected role output folder. Require one `SINGLE`/unfiltered APK per
role, safe filename-only references and non-linked in-project output paths;
reject an actual split APK even if sidecar metadata claims otherwise. Both
products must have distinct bytes, and their hashes must remain unchanged during
inspection. The wrapper remains `verify-android-release-artifacts.ps1`, with the
same version/report arguments and optional explicit `-Aapt2Path`. Install Python
and SDK build-tools 36.1.0; SDK discovery uses `ANDROID_HOME`, `ANDROID_SDK_ROOT`
or the known local SDK property only. A custom tool path is trusted operator
input, not a claim that the SDK executable was independently attested.

Each artifact records `identity_verification=AAPT2_PACKAGED_MANIFEST`; its hash
is covered by the candidate's complete manifest/source binding. Reports refuse
overwrite and remain `distribution_eligible=false` and
`deployment_accepted=false`. Packaged identity inspection is neither signature
verification nor proof of Firebase/APNs, runtime behavior or an approved signing
identity. Existing local-output inspection is not clean-current-source build
evidence; the changed checker needs fresh builds and its own immutable CI.

Local verification passes 15 new checker tests within 56 mobile-script tests,
plus 241 infrastructure tests including CI mutation controls. Both the Python
CLI and PowerShell wrapper inspect the existing two APKs with real SDK aapt2.
Both role release assemblies then passed in a fresh Gradle invocation (135 tasks,
31 executed, 104 up-to-date). The wrapper inspected those outputs and the full
new manifest was bound to an explicitly dirty `WORKSPACE_SNAPSHOT`; this is local
incremental-build/SDK evidence, not clean-source CI or a signed release claim.
The new release assembly also exposes Kotlin-metadata parsing warnings from R8
under Kotlin 2.4.10 / AGP 9.0.1. Compilation or APK identity success does not
resolve that toolchain debt. Verify the actually resolved R8 version against
[Android's Kotlin compatibility table](https://developer.android.com/build/kotlin-support)
and fix/retest minification before accepting a distributable candidate; do not
suppress the warning or disable shrinking to pass the gate.

### Contracts and combined candidate

The exact OpenAPI packet contains `launch-api.openapi.json`,
`local-compatibility-api.openapi.json` and `openapi-manifest.json`. Its canonical
whole-schema digests must be listed in the backend clean-source artifact record,
not inferred from the source operation inventory. CI retains the packet and
binding for 30 days; an approved release custodian must preserve it in the
controlled release evidence store before CI retention expires. The launch
profile has no legacy global-admin routes. Source export isolation and a matching
digest do not establish runtime permissions, served topology or acceptance.
The OpenAPI jobs passed on `17a94df` above; changed candidates still require
their own immutable successful execution.

GAP-001 remains open until all of the following refer to one clean commit:

1. The complete intended source set is reviewed and committed on a protected
   branch or pull request, with clean status in a fresh checkout.
2. Remote CI passes every required job for that exact commit.
3. CI publishes the generated source-contract inventory, migration head,
   dependency locks, OpenAPI digest, web manifest, Android/iOS verification
   manifests, test evidence and backend image SBOM/provenance.
4. A registry supplies the immutable backend image digest.
5. Distribution signing produces passenger and driver mobile artifacts whose
   identities and hashes are added to the release manifest.
6. A reviewer approves release notes, unresolved limitations and the applicable
   forward migration decision.

## Migration and rollback decision

This candidate adds no migration beyond head `20260908_0052`. Promotion must run
`alembic upgrade head` from a production-like copy and verify the no-op/current-
head path. Once a real environment has executed an accepted migration, schema
downgrade is not the default rollback mechanism. Application rollback is allowed
only to a compatibility-tested artifact that supports the current schema;
otherwise use a reviewed forward fix. Never silently repair conflicting ride,
financial, authorization, audit or incident history to make a downgrade pass.

## Explicitly unaccepted

This baseline does not establish production hosting, managed-database recovery,
provider delivery, legal city approval, real tariffs, operations staffing,
security review, signed mobile distribution, physical-device acceptance,
accessibility, capacity, failover, staff rehearsal, closed cohort, real-user
pilot, public city launch, or national rollout. Those remain ordered requirements
in `gaps.md` and `testing_execution_map.md`.
