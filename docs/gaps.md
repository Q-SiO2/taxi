# TaxiMobile — Real-World Deployment Gap Audit

## 1. Audit status

**Audit date:** 2026-09-09

**Repository migration head:** `20260908_0052`
**Decision:** **not ready for a public launch or live city pilot**

The dated [readiness assessment](readiness.md) supplies the weighted engineering
percentage and fresh audit checks. The [delivery workflow](workflow.md) explains
how to turn these gaps into implementation tasks and accepted evidence. Neither
document closes a gap by assigning a percentage.

TaxiMobile has a broad provider-independent implementation, but source delivery
is only one part of operating a transport platform. The repository cannot prove
that a city has authorized the service, that licensed drivers will participate,
that maps and routing work on Moroccan roads, that money can be reconciled, that
urgent cases will be answered, or that production systems can survive failure.

This document is the authoritative open-work register for real-world deployment.
It does not weaken the product contracts in the other documents. When a gap
reveals a missing product decision, that decision must be approved in the owning
document before code is changed.

## 2. Meaning of status and priority

| Label | Meaning |
| --- | --- |
| **Implemented in source** | A code/schema path and applicable automated tests exist in this working tree. |
| **Locally verified** | Relevant checks passed in the development workspace. This is not a signed release or production proof. |
| **CI-wired** | A workflow definition exists in the working tree. Commitment and a passing immutable remote run must be established separately. |
| **Deployment-accepted** | A named owner approved dated evidence from the real target environment, provider, city, or device. |
| **P0** | Blocks any public launch or live pilot carrying real passengers, driver documents, location, or money. |
| **P1** | Must close before a scaled public service; may also block a narrowly controlled pilot when the pilot scope touches it. |
| **P2** | Reliability, maintainability, and scale work that must be scheduled and measured before national expansion. |
| **Deferred** | Explicitly outside the current launch scope and not to be exposed as an available capability. |

A controlled internal technical rehearsal may start before all P0 gaps close only
if it uses synthetic accounts/data, no public recruitment, no real passenger
transport, no real driver identity files, and no production money. Calling such a
rehearsal a “pilot” does not make it one.

## 3. Audit method and evidence limits

The audit compared all authoritative files in `docs/` with:

* Kotlin Multiplatform passenger/driver and web source under `TaxiMobile/`;
* FastAPI domains, workers, migrations, and tests under `backend/`;
* local and production-blueprint deployment files under `infra/`;
* the committed GitHub Actions workflow;
* asset manifests, release validators, and source-contract tests; and
* the current Git working tree and prior local verification from this workspace.

The reviewed workspace reports successful backend unit/API tests, all current
fresh-PostGIS integration slices, Android/shared compilation, JavaScript and
Kotlin/Wasm compilation, and mobile/source-contract tests. On 2026-09-28,
immutable commit `de69829a649715ad7768756e285fedfde2fa846a` passed the complete
push and pull-request workflows for backend/PostGIS, Android/shared, both iOS
Release simulator applications, documentation/provenance, wrapper integrity,
dependency submission/review, JavaScript/Wasm browser tests, and packaged web
compatibility. This is remote source/build evidence, not review, signing,
physical-device, provider, hosted-environment, or deployment acceptance. On
2026-09-02 the workspace completed both Gradle
`jsBrowserTest` and `wasmJsBrowserTest` locally. That is component/browser-runner
evidence, not a full critical-journey E2E run or acceptance across the required
browser matrix.

On 2026-09-02 the provider-independent account-recovery/session wave applied the
complete migration chain through `20260902_0046` to a fresh isolated PostGIS
database and passed all 464 backend tests (174 dependency deprecation warnings).
The mobile contract validator covered 79 HTTP plus one WebSocket operation; the
shared JVM suite and both Android passenger/driver debug Kotlin compiles passed.
The documentation validator also passed with migration-head and testing-phase
consistency. These are dirty-workspace local results, not immutable CI, hosted,
physical-device, security-review, or deployment acceptance.

The latest completed full regression passed a fresh isolated PostGIS rebuild on 2026-09-09 through
`20260908_0052` with **992 backend tests**, no failures/errors/skips, and dependency
deprecation warnings. This includes place authority, the active-ride coordination
lifecycle, notification policy, source-deadline/device-failure contracts,
scheduling eligibility/readiness, successful handoff/fallback transaction rollback/replay,
twelve observed two-session scheduling lock races, four account-containment/
assignment lock races, two location/handoff lock races, seven live-command lock races, expiry-worker skip/retry
and operational-state dispatch guards,
competing and mixed-origin assignments, direct-write uniqueness and conflict-refusing migration checks,
plus migration ownership, actual CLI contention, transaction/process-release,
timeout configuration, blocked-DDL rollback/retry and statement-cancellation checks,
and real live-event fanout. The full run also includes three deterministic
dispatch-contention cases, 41 passenger-workload, 23 paired-cash and 12
open-loop-capacity unit cases,
and seven actual CLI/socket/PostGIS cases: two for durable offer cancellation
and fail-closed registration throttling, three for completed cash journeys
under different fee configurations, and two for errors after completion or
settlement has committed. A separate focused run passed all 74 workload/contention
cases, a second focused run passed all 28 scheduled-acceptance and
live-protection cases, and a third passed all 13 account-assignment authority
cases. It also includes the staff-grant maker-checker, continuity and bounded
initial-quorum cases added with migration 0049. The
expanded contract gates cover **83 mobile HTTP plus one WebSocket operation** and
**112 web HTTP operations**. The current shared JVM suite contains **183 tests**;
its place-serviceability, recovery-code, foreground driver-location and
coordination and scheduled-notification cases, the full suite, both Android role compiles, and JS/Wasm
compilation are locally verified.

The latest full-backend JUnit run is **992 tests**, zero failures, errors, or
skips, 175 dependency warnings, and 464.24 seconds. This duration is not capacity
evidence. The preceding generated
JUnit evidence remains `backend/build/security-incident-full-tests.xml` at
**956 tests**, zero failures, errors, or skips, 175 warnings, and 553.126 seconds.
Both include the
structured-log configuration/rotation, monitoring/alert mutation, open-loop
capacity, strict four-phase profile, explicit database-pool configuration and
pool-telemetry additions; the separate candidate-image
ingestion preflight is runtime evidence outside the pytest count.

Migration `20260907_0050` adds the focused security-incident register and
`20260907_0051` adds one-time referenced postmortem completion. The current
regression also covers the fixed-severity aggregate deadline collector, fail-
closed scrape rendering and immutable alert mutations. Migration `20260908_0052`
adds four closed incident responsibilities, exact-market assignee eligibility,
one-active-role uniqueness and append-visible reassignment history.

The historical audit began from extensive modified and untracked source, but the
current GAP-001 candidate is committed, clean, and has passing immutable remote
CI at `de69829a649715ad7768756e285fedfde2fa846a`. It still has no independent
review approval, signed mobile artifact, or registry
container digest. This audit also did not inspect a live cloud account, production
database, app-store account, Firebase project, routing host, real payment
statement, legal authorization, or operator staffing record.
`main` promotion protection was subsequently configured and read back on
2026-10-02 under explicit owner approval; actual review remains absent.

“No implementation found” means no matching user-facing contract and end-to-end
source path was found during this repository audit; it does not claim that an
unavailable external system cannot provide the capability.

## 4. Current implementation inventory

| Area | Implemented in the repository | What that does not prove |
| --- | --- | --- |
| Identity | Registration/login, rotating refresh sessions, backend/mobile session listing and confirmed revocation, password change, offline-code creation/reset, suspension, server-side roles, operations audience, scoped grants, TOTP/recovery MFA, recent-MFA, secure cookies and CSRF | Verified contact ownership, secure-save UX acceptance, production recovery, support identity proofing, privacy-right workflows |
| Drivers | Profiles, vehicles, credentials, availability, applications, requirement versions, protected document adapters, reviews, city authorizations, route/schedule participation, earnings | Local licensing accuracy, real document storage/scanning, reviewer capacity, recruited supply, payout |
| Rides | Estimates, immediate request lifecycle, sequential offers, assignment, cancellation, completion, receipts, fixed-route-linked and scheduled handoff flows, and closed-code assigned-ride coordination | Real dispatch quality, navigation, physical service delivery, coordination usability/delivery, weak-network recovery |
| Matching | Eligibility, deterministic offer ordering, fairness accounting, decline/expiry, leases, worker loop, aggregate simulation | Peak capacity, multi-instance contention under realistic load, field fairness or sparse-supply performance |
| Places | Authenticated normalized search/reverse APIs, fail-closed provider selection, Nominatim-compatible adapter, active city/on-demand service authority, exact PostGIS pickup eligibility, shared passenger search/retry/selection UI and map fallback | Approved provider/data license, query-egress privacy, multilingual city relevance, capacity, physical usability or saved places |
| Pricing | Versioned city/operator/service tariffs, fixed-route fares, booking fees, operator fees, immutable quote/ride/payment/earning snapshots | Legal tariff approval, operator commercial agreement, real receipt and accounting acceptance |
| Payments | Cash, manual bank/M-Wallet transfer claims, recipient/capability versions, scoped reconciliation, earnings and operator-funded refunds | Real recipient ownership, statement fidelity, cash custody, refund execution, operator-driver settlement/payout |
| Notifications | In-app history, live refresh hints, Postgres cross-instance transport, FCM/APNs adapter boundaries, retry/dead-letter behavior | Real Firebase/APNs projects, device delivery, credential rotation, paging ownership, delivery SLO |
| Support and safety | Participant records, scoped queues, assignment, lifecycle actions, notes, safety handoff, overdue alerts, pager adapter, legal holds and retention erasure | Staffed response, emergency policy, real pager, incident drill, lawful retention and backup expiry |
| National control plane | Markets, operators, cities, service areas, configuration bundles, maker-checker scoped staff authority with two-admin continuity, readiness evidence, pause/resume, closeout | Authoritative roster/recertification, truth or sufficiency of uploaded evidence, city authorization, operational competence, pilot success |
| Recruitment | Public city catalog, applications, versioned requirements, protected files, review and authorization, aggregate onboarding metrics | Public-hosting security, actual recruitment, licensing review policy, safe production file processing |
| Fixed routes and scheduling | Versioned routes/directions/stops/geometry/fares, publication, catalog, driver authorization, scheduled review/commitment/opening/fallback | Regulatory approval, map/routing accuracy, service operations, passenger comprehension, punctuality |
| Analytics | Typed events, aggregate definitions, refresh worker, small-cell suppression, operations views, retention | Production event completeness, threshold ownership, usefulness, fairness governance, monitoring accuracy |
| Mobile UI | Passenger/driver flavors and schemes, map-first Compose surfaces, English/French/Arabic, RTL, asset fallbacks | Signed store releases, physical-device quality, accessibility, usability, production providers |
| Web UI | Applicant portal and protected operations modules for rollout, recruitment, pricing, routes, scheduling, analytics, cases, payments, staff approval, security incidents/postmortems, and audit; JS/Wasm CI, compatibility packaging, source-map exclusion and bundle ceilings passed on immutable commit `de69829a` | Full browser E2E, production hosting/CSP, accessibility, authoritative rosters and staff-process acceptance |
| Infrastructure | Local Compose, production Compose blueprint, separated API/worker roles, health/readiness, validators, backup/restore scripts, bounded role logs, and hardened Prometheus/Alertmanager/Loki/Alloy/Grafana with immutable dashboards | A running production environment, managed database, TLS/DNS, secrets, registry, accepted hosted metric/log targets, real pager, HA or restore RTO |

## 5. P0 — launch-blocking gaps

### GAP-001 — Establish an immutable release baseline

**Current gap (updated 2026-10-02):** implementation is committed on the
release-baseline branch, with complete passing push/PR evidence for server
commit `17a94df` recorded in `release_baseline.md`. Newer source slices must acquire their own
complete immutable CI; a passing predecessor does not certify a changed checkout.
Draft pull request 43 exists, but independent review,
signed distributable artifact manifests, a registry image digest, and release
approval are still missing. Historical dirty-workspace results below are not
evidence that the current checkout remains dirty.
Protected `main` promotion rules are now configured and verified; this removes
the protection-configuration prerequisite, not the independent review gate.

**Risk:** tests, migration history, binaries, and deployed source can silently
refer to different code. Rollback and incident investigation become unreliable.

**Required closure:** review and intentionally stage the complete change set;
remove only confirmed generated/local debris; run the complete verification suite
from a clean checkout; protect the release branch; record migration head, OpenAPI
digest, Android/iOS versions, web bundle digest, dependency locks, image digest,
and release notes.

**Acceptance evidence:** clean `git status`; reviewed commit/PR; passing CI for
that commit; signed release manifest mapping every artifact to the commit and
`20260908_0052`; tested forward migration and documented forward-fix/rollback decision.

**Implementation progress (2026-09-01):**
`infra/scripts/generate_release_evidence.py` now refuses a dirty release candidate
unless the caller explicitly requests a non-release `WORKSPACE_SNAPSHOT`. It
records commit/tree identity, dirty counts, migration head, reviewed source-input
hashes, optional artifact hashes, and CI metadata while always distinguishing
provenance from deployment acceptance. The documentation/provenance CI job
generates this record from a clean checkout. GAP-001 remains open until the full
working tree is reviewed, committed, built, signed, and accepted.

**Implementation progress (2026-09-09):** the web CI package now emits an
81-file hash/size manifest and binds that manifest's hash to the exact clean
commit, tree and migration evidence before retaining both records in the run
summary. Android does the same for distinct passenger/driver APK metadata and
iOS does so for deterministic passenger/driver simulator-bundle hashes. Mobile
verification manifests are explicitly `distribution_eligible=false` and name
unaccepted signing, provider, device and App Store boundaries. Local records are
correctly labeled dirty `WORKSPACE_SNAPSHOT`; none substitutes for the still-
missing immutable remote run, signed artifacts or deployment acceptance.

**Implementation progress (2026-09-10):** `release_baseline.md` now records the
candidate label, included source scope, migration and rollback boundary, local
verification matrix, explicit non-acceptance limits and the evidence required
from one clean commit. A fresh local candidate run passed 992 backend tests,
restored 81 tables at migration 0052, removed its temporary target/dump and left
zero test clones with temporary `CREATEDB` authority revoked. The infrastructure
and mobile release-tool suites, Gradle client gates and eight-scenario packaged
Chrome/Firefox smoke also passed. This establishes a reviewable local candidate,
not closure: clean commit/PR status, remote CI, signed distributable artifacts,
registry image digest and reviewer approval are still required.

**Implementation progress (2026-09-11):** the blocking image-scan failure was
reproduced with CI's Trivy version: the Debian runtime exposed 54 unfixed
high/critical OS findings while application packages had none. The backend image
now uses a digest-pinned CPython Alpine runtime, applies Alpine's available
security upgrades, retains the non-root account and private directory modes, and
extends the Linux lock with the official CPython 3.12 musllinux `uvloop` hashes
for both supported architectures. A local production-image build, non-root
runtime/import smoke and exact high/critical scan passed with zero findings.
The remote clean-commit scan, registry digest and promotion evidence remain
required; this implementation progress does not accept GAP-001.

**Implementation progress (2026-09-27):** the next immutable CI run exposed a
monitoring smoke assertion that still expected 13 operations panels although
the reviewed provisioned dashboard and its source contract contain 26. The
runtime assertion, Windows deployment smoke, operator documentation, and MON-T5-13
acceptance row now agree on 26; a source validator prevents CI from silently
regressing to the stale count. Monitoring-tool output is captured into a bounded,
redacted failure annotation, and Gradle diagnostics retain failure summaries and
root causes ahead of repetitive stack tails. GAP-001 remains open until fresh
remote checks, including the iOS simulator and repository dependency-graph
submission, pass on the candidate commit.

**CI compatibility follow-up (2026-09-27):** the fresh run also showed the
Android SDK setup step failing before Gradle, with the pinned legacy Actions
runtime being forced to Node 24 after Node 20 retirement. The workflow now pins
current Node-24-compatible releases of checkout, Java/Python setup and Android
SDK setup by immutable commit SHA. This addresses action-runtime compatibility;
the exact Android setup failure still needs confirmation from a rerun because
GitHub restricts raw job-log access to repository administrators. The same run
confirmed dependency submission is blocked by the repository's disabled
Dependency Graph setting; the security job remains required and was not
weakened.

**Cross-platform follow-up (2026-09-27):** the Node-24-compatible Android SDK
setup completed on the next remote run, which advanced into and failed during
the shared JVM/Android-host test step. Authenticated job-log inspection traced
that failure to HTTP 500 while fetching the Kotlin compiler dependency, before
tests executed. The local equivalent
`:shared:jvmTest :shared:testAndroidHostTest` passes on Windows in 3m17s. CI
failure output is now captured through the bounded redaction helper. The iOS annotation exposed a
missing explicit `platform.Foundation.create` import in the Keychain token
store; the import is fixed, but iOS compilation requires macOS CI and remains
unverified until that run completes. The disabled GitHub Dependency Graph is a
repository setting blocker, not a reason to remove dependency submission.

**Native compilation follow-up (2026-09-27):** the next candidate run passed
backend and web verification. The macOS compiler then reported missing native
extension imports for `NSLocale.preferredLanguages` and C pointer-variable
`value`, plus a nullable document media type passed to the upload model. Those
imports and an explicit null rejection are now present; the document-picker
source regression guards both null and unsupported media rejection. This patch
still requires the macOS compile/test run. It does not certify Keychain runtime
bridging, error handling or atomic token persistence: the read-only architecture
audit identified those as separate native authentication risks. The same audit
found established PostgreSQL LISTEN disconnect recovery and socket revocation
coverage needing remediation before release. These findings must not be hidden
by successful method/path contract validators or compilation alone.

**Listener recovery follow-up (2026-10-01):** GAP-009 now contains bounded
termination/probe/re-registration and listener-aware API readiness source plus
unit/API and owned-connection PostGIS regressions. Ongoing socket authorization,
mobile unchanged-ready resubscription and hosted failover remain open. A source
repair does not supersede those separate security/device/operational findings.

**Keychain follow-up (2026-09-27):** the subsequent macOS run advanced through
the iOS production-source compile and failed only because a common test used the
Native experimental `assert` API. Replacing it with `kotlin.test.assertTrue`
removes that opt-in. The same compile proved the former Kotlin-map-to-
`CFDictionaryRef` and `CFTypeRef`-to-`NSData` casts could never succeed. The iOS
store now creates owned Core Foundation query/data values, validates the copied
type, checks read/update/add/delete status codes, and persists both tokens in one
versioned Keychain item. Common tests cover envelope corruption and coordinator
storage failures; source guards reject restoration of the impossible casts or
split writes. This patch still requires a clean macOS run and physical-device
locked/unlocked save/restore/logout acceptance before the native credential
boundary can be accepted.

**iOS linker follow-up (2026-09-27):** production and test Kotlin compilation
now pass on Xcode 26.2. The Gradle native-test link then fails because MapLibre
Compose 0.14.0's published iOS KLIB embeds the publisher's absolute
`/Users/runner/work/maplibre-compose/...` framework path and an Xcode 26.6 Swift
library path; this is the exact open upstream defect `maplibre-compose#824`, not
a TaxiMobile source or Keychain link error. CI now keeps compilation blocking,
links both role applications through their exact-version Xcode Swift package,
and states explicitly that no iOS test execution occurred. A future reviewed
MapLibre upgrade or upstream fix must restore native test execution; physical-
device acceptance remains mandatory.

**Swift application-link follow-up (2026-09-28):** the first Xcode application
build resolved and compiled the pinned Swift packages, then correctly failed in
the checked-in Swift shell before linking. Kotlin/Native exports the driver-
document completion callback with a `KotlinUnit` result, while the UIKit picker
coordinator owns a Swift `Void` callback. Passing the exported closure through
directly therefore failed Swift compilation. The shell now wraps the callback
and explicitly consumes `KotlinUnit`; a source regression guard rejects both the
former direct pass-through and removal of the adapter. This requires a fresh
macOS Xcode build for both roles and does not yet establish application linking.

**iOS package-lock and application-link follow-up (2026-09-28):** immutable
commit `33d699fbcd24c0eb06c5a27c9ea13acddf5ba56e` passed Kotlin production/test
compilation and linked both Passenger and Driver Release simulator applications
in independent push and pull-request jobs. Both jobs also generated the
two-product verification manifest, then correctly refused source evidence
because Xcode had created a previously absent, untracked `Package.resolved`.
That failure exposed a real reproducibility gap rather than an application
failure. The exact 14-package resolution is now committed with immutable
revisions; both role builds disable automatic package resolution, use a dedicated
lock-keyed SwiftPM cache, and have a 45-minute outer job bound. Mutation tests
reject branch pins, revision drift, root-package disagreement, cache-key drift,
or removal of either no-resolution flag. The repository Dependency Graph and
Dependabot alerts are now enabled and the repository SBOM endpoint responds, but
the dependency and iOS evidence jobs still require a passing run on this new
commit. This confirms simulator application linking only—not native iOS test
execution, signing, provider configuration, physical-device behavior, or
deployment acceptance.

**Immutable candidate follow-up (2026-09-28):** corrected commit
`de69829a649715ad7768756e285fedfde2fa846a` passed both the push run
([36430942057](https://github.com/Q-SiO2/taxi/actions/runs/36430942057)) and
pull-request run
([36430946742](https://github.com/Q-SiO2/taxi/actions/runs/36430946742)). The
push submitted the Gradle graph; the pull request passed dependency review. Both
macOS jobs restored the lock-keyed Swift package cache, compiled Kotlin
production/test sources, linked Passenger and Driver Release simulator apps,
generated the two-product manifest, and bound it to clean-source evidence. The
known MapLibre Compose 0.14.0 defect still prevents native iOS test linking, and
the run does not supply review, branch protection, signing, physical-device,
registry-digest, provider, or deployment acceptance. GAP-001 remains open.

**Immutable server follow-up (2026-10-02):** commit
`2d6a68b04eccd793d5d071b8f26bba67568bf63b` passed both
[push CI](https://github.com/Q-SiO2/taxi/actions/runs/37000510927) and
[PR CI](https://github.com/Q-SiO2/taxi/actions/runs/37000515435). These complete
backend, mobile, web, documentation/security and iOS simulator-build runs certify
only that source candidate's automated gates, not signing, native iOS execution,
review approval, physical devices, registry promotion or deployment. The
subsequent Android protected-storage patch needs independent immutable CI.

**Immutable Android follow-up (2026-10-02):** commit
`cc19776fdc804093bffdfe92023679258a66a023` subsequently passed both
[push CI](https://github.com/Q-SiO2/taxi/actions/runs/37023593864) and
[PR CI](https://github.com/Q-SiO2/taxi/actions/runs/37023603230), including both
iOS Release simulator application links. These runs supersede the preceding
pending-CI status for that Android patch only. Native iOS execution, physical
Keystore/storage, signing, registry promotion and deployment remain unaccepted.
The subsequent OpenAPI evidence tooling requires its own immutable CI.

**Exact API-contract evidence follow-up (2026-10-02):** the release pipeline now
exports whole OpenAPI schemas for two explicit route profiles: launch without
legacy `/admin`, and local compatibility with it. Canonical UTF-8/LF bytes and
SHA-256 cover full request/response/component/security definitions, not only
operation names. The exporter isolates import-time configuration from deployment
settings, never starts a lifespan or contacts providers/database, and refuses
to overwrite existing reports. The source manifest has no authorization or
deployment acceptance. CI binds both schemas plus their manifest to backend
clean-source evidence, uploads the packet for 30 days and summarizes digests.
Mutation checks prevent dropping either schema, bypassing generation or weakening
retention. Local real-factory and adversarial fixture tests remain distinct from
this candidate's required immutable CI, served-staging schema/authorization
checks, signed artifacts, registry digest and independent approval.
Local verification passes 15 exporter fixture/worker cases and three CI mutation
cases within 222 infrastructure tests, 47 focused backend factory/system API
cases, a fresh zero-failure/error/skip JUnit run for the three new backend cases,
and actual two-schema/manifest hash reconciliation against an explicitly dirty
workspace evidence record. No new full migrated-PostGIS or physical/hosted
acceptance is claimed. Source scope remains approximately 84%; P0 acceptance
remains 0/19. This fills the OpenAPI-digest prerequisite, not GAP-001 closure or
a new API policy.

**Protected promotion and registry implementation (2026-10-02):** verified main
protection requires passing up-to-date provider-bound checks and one independent
latest-push approval, including administrators, with stale approvals dismissed,
force pushes/deletion disabled and conversations resolved. The owner delegated
the no-cost technical setup; GHCR is selected only for backend image storage.
The publication job is main-push-only, has scoped package-write permission and
waits for all push verification jobs. It carries the exact scanned image and
SBOM through same-run/attempt hash-bound evidence, checks before Docker load,
checks the loaded ID, and verifies a digest-pinned registry pull before emitting
no-acceptance provenance. No post-scan rebuild or mutable `latest` deployment is
allowed. Tests cover corruption, identity drift, acceptance forgery, wrong loaded
and pulled images, foreign/ambiguous digest and failure redaction; CI mutations
preserve gating and handoff. Local Docker is unavailable; no actual push/pull or
registry digest is claimed. PR 43 stays draft/unapproved/unmerged; source scope
remains approximately 84%, P0 acceptance 0/19. Independent review, signing and
release approval remain open. See `release_baseline.md` for retention and trust
boundaries.

### GAP-002 — Provision and accept a real hosted environment


**Current gap:** deployment files are provider-neutral blueprints and a strict
inventory schema now exists, but no completed inventory or accepted host, domain,
TLS ingress, DNS, immutable image registry, secret manager, network policy, or
separated production environment exists.

**Risk:** the application cannot be safely reached, operated, rotated, or
reproduced. A free test host is not automatically suitable for identity,
location, document, safety, or payment data.

**Required closure:** choose a jurisdictionally acceptable host and data region;
create separate development/staging/production environments; deploy images by
digest; terminate TLS; restrict database, worker, monitoring, scanner, and routing
networks; store and rotate secrets; enforce allowed hosts/CORS; document ownership
and cost limits; rehearse deployment and rollback.

**Acceptance evidence:** architecture and data-region approval; DNS/TLS scan;
network and IAM review; secret rotation record; staging deployment report;
production change record; digest-pinned deployment; rollback rehearsal with
measured recovery time.

**Implementation progress (2026-09-28):**
`infra/deploy/production-environment-inventory.template.json` and
`infra/scripts/validate_production_environment_inventory.py` define the missing
provider-neutral control record. CI validates the deliberately `NOT_STARTED`
template. An external record can pass `--require-accepted` only with distinct
development/staging/production account, network, secret and database references;
exact DNS/TLS origins and host/CORS policy; the reviewed 12-service public/private
topology; digest-pinned API/worker/migrator/scanner images; network/IAM, secret
rotation, cost, deployment, migration and rollback evidence; measured rollback
within the approved RTO; and architecture, data-region, security, operations and
cost approvals. The record contains references only and can accept GAP-002 only;
it cannot accept T5 or deployment. The committed template has no provider claims,
so GAP-002 remains open.

### GAP-003 — Operate managed PostGIS, migrations, backups, and restoration

**Current gap:** migrations and local backup/restore tooling exist, but there is
no production database, encrypted backup policy, point-in-time recovery, tested
staging restore, capacity baseline, or verified expiry of data removed by
retention workers.

**Implementation progress (2026-09-09):** the guarded fresh-PostGIS runner now
emits full JUnit, secret-free database metadata and a bounded T3 system report.
The latest run passed 992 tests, verified migration 0052 and PostGIS, exercised
named lock/race/worker-reclaim/reconciliation cases, removed one strictly named
stale test clone, found zero residual clones and confirmed temporary local
`CREATEDB` authority was revoked. A guarded logical backup then restored 81
public tables and 8,511 aggregate rows at migration 0052, matched PostGIS and
schema-object totals, accepted a no-op upgrade, and removed the restore target
and dump. The combined report supports all six T3 evidence kinds and marks
evidence complete while refusing T3/deployment acceptance. Measured production
RPO/RTO, encrypted managed backups, hosted PITR/failover, retention expiry and
owner approval remain open.

**Risk:** permanent loss, corruption, migration outage, privacy retention breach,
or unrecoverable city operations.

**Required closure:** provision managed PostgreSQL/PostGIS with private access,
encryption, least-privilege roles, monitoring and PITR; define RPO/RTO; rehearse
`20260908_0052` migration from a production-like copy; test restore into isolated staging;
verify PostGIS/version/index state and application readiness; verify that expired
personal data also leaves backups according to approved policy.

**Acceptance evidence:** approved RPO/RTO; automated encrypted backup schedule;
successful restore report with timings and integrity counts; migration rehearsal;
failover test; backup-retention and legal-hold reconciliation signed by security,
operations, and legal owners.

**Implementation progress (2026-09-28):**
`infra/deploy/managed-postgis-evidence.template.json` and
`infra/scripts/validate_managed_postgis_evidence.py` define the protected
provider-neutral GAP-003 record. CI validates the deliberately `NOT_STARTED`
template. An external record can pass `--require-accepted` only when it binds the
accepted environment and immutable source to private TLS/encrypted PostgreSQL 16
with recorded PostGIS compatibility; non-superuser application and separated
migration/backup/monitoring authority; approved RPO/RTO and connection headroom;
a current-`20260908_0052` production-like migration rehearsal; encrypted PITR and
cross-failure-domain retention; isolated staging restore and provider failover
within RPO/RTO; readiness/schema/count reconciliation; retention/legal-hold and
backup-expiry proof; and engineering, security, operations and privacy/legal
approval. It records references and aggregate timings only and cannot accept T5
or deployment. No managed database has supplied that evidence, so GAP-003 remains
open.

### GAP-004 — Approve one real city, operator, and launch scope

**Current gap:** the source can record market/operator/city readiness, but no real
city has accepted legal authority, service category, operating entity, service
area, tariff, fixed-route permission, scheduling rules, fee policy, safety
responsibility, data handling, or launch criteria.

**Risk:** technically valid configuration may be illegal, commercially
unsustainable, unsafe, or operationally ownerless.

**Required closure:** select exactly one pilot city and named operator; obtain
local legal/regulatory review; approve the launch service type, geographic area,
hours, fares/fees, fixed-route and scheduling scope, passenger/driver terms,
complaint and safety ownership, pause authority, and measurable go/no-go criteria.

**Acceptance evidence:** dated approvals linked to the active configuration
bundle; named accountable people; expiry/review dates; public terms; readiness
gate review by a person other than the submitter; explicit owner authorization to
enter `PILOT`.

**Source-control progress (2026-09-28):** configuration approval and all
allowlisted readiness decisions now reject the recorded configuration submitter,
the protected web review explains that separation, and the migrated two-city
integration journey uses a city-manager maker with a platform-admin reviewer.
The decision remains scoped to the exact configuration version and records the
reviewer and time in audit while retaining only a bounded evidence reference.
This does not select a real city/operator, approve a tariff or legal basis, name
an operational owner, publish terms, or authorize `PILOT`; GAP-004 therefore
remains externally **NOT STARTED**.

**Evidence-gate progress (2026-09-29):**
`infra/deploy/pilot-city-launch-approval.template.json` and
`infra/scripts/validate_pilot_city_launch_approval.py` now define a strict
protected record for the external decision. Acceptance requires one real
Moroccan city and legal operator, the exact active configuration, explicit
service/payment scope with cash retained, public Arabic/French/English terms,
nine accountable functions, bounded pilot exposure, all ten current readiness
decisions reviewed independently of the submitter, and six approvals including
product-owner authorization. The committed template is deliberately
`NOT_STARTED`, accepts neither T6 nor deployment, and cannot be used to invent
the missing city/operator/legal decisions.

### GAP-005 — Establish production operations identity and governance

**Current gap:** scoped grants, operations sessions, MFA, bootstrap/enrollment
CLIs and typed-confirmed web grant create/revoke reviews exist, but there are no
production staff accounts, factor enrollment, recovery drill, authoritative
joiner/mover/leaver process, periodic access review, or dual control for the most
sensitive grant, financial and rollout actions.

**Risk:** lockout, excessive privilege, insider abuse, orphaned access, or an
unavailable administrator during a live incident.

**Required closure:** define roles and separation of duties; bootstrap from an
audited trusted terminal; enroll named factors and securely issue recovery codes;
exercise recovery without bypassing audit; approve grant/retirement procedures;
require independent review for activation, money, sensitive documents, and city
launch; schedule access recertification.

**Acceptance evidence:** account and grant register; MFA/recovery drill; least-
privilege test accounts; access-review sign-off; leaver revocation drill; audit
records for bootstrap, grants, step-up, and sensitive actions.

**Evidence-gate progress (2026-09-29):**
`infra/deploy/operations-identity-governance.template.json` and
`infra/scripts/validate_operations_identity_governance.py` now define a strict
protected record for these external controls. Acceptance requires an
authoritative roster/JML source, three distinct platform-administrator quorum
duties, explicit rollout/pricing/payment/document/support/safety assignments,
independently reviewed TOTP and recovery custody for every assigned account,
bounded access-review and leaver policy, eight exercised control drills, fixed
audit references and four owner approvals. The committed record is deliberately
`NOT_STARTED`, contains references rather than names or secrets, accepts neither
T5 nor deployment, and cannot fabricate production accounts or human drills.

### GAP-006 — Accept production maps, routing, and navigation

**Current gap:** MapLibre rendering, a neutral fallback style, and normalized
Valhalla/GraphHopper route contracts exist. There is no approved production tile
and style source, attribution/offline/cache policy, promoted Morocco routing
graph, data-refresh process, route-quality benchmark, traffic policy, or accepted
Arabic/French narration/device navigation result.

**Risk:** wrong pickup/drop-off, unusable directions, legal attribution breach,
unexpected provider cost, stale roads, or navigation failure during a ride.

**Required closure:** choose Valhalla or GraphHopper for launch; build and promote
a pinned Morocco graph; choose a sustainable tile/style source; use a restrained
generic style consistent with the UI; define data licensing, attribution, cache,
refresh and rollback; test urban, peri-urban, restricted, one-way, roundabout and
fixed-route cases in the pilot city; accept localized maneuver text and rerouting.

**Acceptance evidence:** versioned graph/style artifacts; license and attribution
review; route benchmark with expected tolerances; device traces; navigation and
reroute matrix in all required languages; provider outage/fallback drill; owner
approval of map appearance and legibility.

**Evidence-gate progress (2026-09-29):**
`infra/deploy/maps-routing-navigation.template.json` and
`infra/scripts/validate_maps_routing_navigation.py` now define a fail-closed
protected acceptance record for GAP-006. It binds one approved Moroccan city
configuration to immutable MapLibre style/tile metadata, a digest-pinned Morocco
routing graph, explicit licensing/attribution/cache/offline/privacy/cost and
refresh/traffic/rollback controls, all six required route-benchmark categories,
four passenger/driver Android/iOS surfaces in Arabic/French/English, seven outage,
reroute, network, rollback and attribution drills, and six owner approvals. An
accepted record must also be supplied the exact redacted output of the existing
routing acceptance command and match its SHA-256; every fixed public scenario
must pass all three languages for the selected Valhalla or GraphHopper provider.
This preserves the current explicit Valhalla Arabic limitation instead of
allowing a paper approval to hide it. The committed record is deliberately
`NOT_STARTED`, contains no provider choice, city claim, raw route trace,
credential or approval, and accepts neither T5 nor deployment.

### GAP-007 — Decide and implement the operational driver-location model

**Current gap:** the source now adopts a foreground-only pilot model. After an
approved driver explicitly stages a fresh coordinate and goes online, Android
and iOS schedule already-authorized one-shot observations every 15 seconds while
available/offered and every 10 seconds during an active ride. Sampling is
disarmed when offline, paused, disconnected, or backgrounded; it never opens a
permission prompt automatically, requests background permission, persists a
client trail, or changes dispatch authority. An unavailable platform observation
backs off for 60 seconds and surfaces a warning. The backend remains authoritative
for timestamp, configured freshness, credible movement, service area, driver/
vehicle eligibility and matching; stale positions are excluded. Assigned
passengers receive only a post-acceptance last-known observation.

The scheduling audit found and implemented the missing direct-handoff readiness
guard: `AVAILABLE` in the booked city/service, the newest observation inside the
configured freshness/60-second future-skew bounds, and the active PostGIS service
area. This runs after professional/city authorization and before assignment.
Failure invokes fallback/unfulfilled; the initial fallback excludes the failed
committed driver. Normal matching also rejects excessively future-dated data.
Source enforcement is not field acceptance or proof of actual pickup readiness.

Fourteen migrated lifecycle variants now include fresh direct handoff, no supply,
professional-ineligibility fallback and nine location/availability/scope failure
cases. Successful replacement, post-flush rollback and repeat handoff are checked
through real services and fresh database reads. Unit tests cover exact freshness
and future-skew boundaries plus missing scope and every non-available status.
Five additional isolated variants prove scheduling lock waits and durable
outcomes for duplicate handoff, cancellation in both orders, driver offline
before handoff and cancellation before acceptance. The offline race deliberately
retains the older cached profile and confirms that the locked read refreshes it.
Broader location/configuration/eligibility races and independent-process tests
remain required; see the `RACE-01` through `RACE-08` progression in `testing.md`.

The model is implemented but not deployment-accepted. No physical long-shift
battery result, weak-network/GPS-loss result, permission-revocation usability
test, dispatch freshness measurement, spoofing assessment, store/privacy review,
or production location SLO exists. Server-side location-row retention/erasure
policy is also not yet approved. Background tracking remains deliberately out of
scope unless field evidence proves the foreground model inadequate and a new
privacy/store review approves it.

**Risk:** a driver may appear eligible at an obsolete location, offers may be
inefficient, navigation/arrival may be wrong, and passengers may lose useful
arrival progress. Adding background tracking casually would create material
privacy, battery and store-review risk.

**Required closure:** field-test and approve or reject the foreground-only model;
exercise direct scheduled-handoff readiness on physical devices under stale,
missing, skewed or outside-area GPS, foreground/background changes, and scope or
availability changes concurrent with handoff; verify fallback/no-supply behavior;
fix the pilot matching threshold and location SLO; approve server retention/
erasure, consent copy, precision, battery ceiling, GPS/spoofing review and pause/
delete behavior; verify no background location entitlement/permission ships. If
the measured model cannot meet safe dispatch targets, document and independently
approve a bounded background design before adding any background capability.

**Implementation progress (2026-09-03):** a pure shared scheduling policy,
Android/iOS lifecycle wiring, authorized-without-prompt requester paths, localized
online disclosure/failure copy, and deterministic inactive/interval/backoff tests
are present. The shared gate still allows only one platform request at a time, and
ordinary app actions take priority over automatic sampling. This is source and
simulator/compiler evidence only until the T4/T7 location matrix passes.

**Callback-race hardening (2026-10-01):** Android and iOS now bind each automatic
lookup to a shared result guard. Backgrounding, connectivity changes, admitted
commands (including logout), and composition disposal invalidate pending results.
Callbacks also recheck foreground/network/action state and the original
availability, vehicle, city, service and ride context before either submitting
an observation or showing unavailable guidance. This prevents an old lookup from
being applied after background/return, command completion or account switch.
It does not cancel native OS work or add background collection. Shared regression
tests cover invalidation and changed-context cases; physical callback timing,
permission revocation and actual battery/network behavior remain T4/T7 evidence.
Local verification for this slice passed 197 shared JVM tests (including seven
result-guard regressions, zero failures/errors/skips), both passenger/driver
Android debug Kotlin compilation tasks, documentation consistency, mobile API
contract validation and source credential hygiene. iOS root verification remains
subject to macOS CI; native test execution and physical-device acceptance are
not claimed by these local checks.

**Acceptance evidence:** approved policy in `rides.md`, `matching.md`, `design.md`
and `security.md`; automated lifecycle/authorization/concurrency tests; Android
and iOS foreground/background traces proving no hidden updates; battery and weak-
network field measurements; stale/spoofed update tests; retention-erasure proof;
privacy/store review; pilot dispatch metrics meeting the agreed freshness SLO.

### GAP-008 — Provide safe place discovery and geocoding

**Current gap:** normalized geocoding and reverse-geocoding source paths now
exist, while production provider approval, multilingual city quality, capacity,
privacy/egress acceptance, physical usability and saved places remain open.
Manual coordinates/map selection are deliberate outage fallbacks, not a complete
mainstream passenger experience on their own.

**Risk:** passengers choose the wrong location, cannot describe pickup clearly,
or abandon booking; operations receive avoidable calls and unsafe roadside
pickups.

**Required closure:** select a sustainable geocoding source or self-hosted data
path; define query minimization, retention, rate limits, localization, result
ranking, landmark handling, service-area validation and outage behavior; keep
coordinates authoritative; never silently send personal labels to an unapproved
provider.

**Acceptance evidence:** approved provider/data license; privacy review; Rabat
and pilot-city Arabic/French/Latin query benchmark; pickup reverse-geocode test;
wrong-city/outside-area behavior; rate-limit and outage tests; physical-user
usability acceptance with manual map fallback.

**Source progress — 2026-09-02:** the backend now has a closed, fail-closed
`disabled|nominatim` provider boundary, normalized authenticated search/reverse
contracts, bounded Arabic/French/English requests, independent account limits,
safe provider errors, attribution, and PostGIS checks against the exact active
versioned city polygon. Reverse responses preserve the requested coordinate.
Hosted configuration requires HTTPS and rejects the shared public Nominatim host.
The shared passenger UI adds a collapsed, debounced, explicitly retryable picker,
city choice, address/street/locality/landmark distinction, outside-pickup warning,
explicit reverse lookup, and map/manual outage fallback. Provider normalization,
API failure/rate behavior, shared coordinator, JVM UI, Android role compilation,
and fresh-PostGIS service-area tests are present.

This gap remains **open for deployment acceptance**. No production geocoder,
data-license approval, hosting/capacity plan, Rabat plus first-pilot-city
Arabic/French/Latin benchmark, privacy/egress review, physical accessibility and
usability evidence, or saved-place design has been accepted. The implemented
adapter must not be described as a production provider decision.

**Selection-race hardening (2026-10-01):** the passenger picker restores the
last query when reopened but exposes results only for the visible normalized
query and city. Editing/clearing/shortening the query hides previous and delayed
results immediately. Reverse lookup now labels only an unchanged selected point:
the pending city/target/coordinate is captured, and completion cannot move a
pickup/destination or label a later selection. No-result guidance is also
discarded after selection/city changes or a live ride starts. Seven regression
tests cover query/city response freshness and pickup/destination label-only
behavior. Local verification passed 204 shared JVM tests with zero failures,
errors or skips and both passenger/driver Android debug Kotlin compilation.
Provider selection, multilingual geographic quality, privacy, saved places and
physical usability remain open; this is source hardening, not GAP-008 acceptance.

### GAP-009 — Accept FCM/APNs and user-visible notification delivery

**Current gap:** adapters, token ownership, retry/dead-letter state, live refresh,
and client receive boundaries exist. No development/staging/production Firebase
projects, APNs configuration, real credentials, device delivery evidence,
credential rotation, notification permission UX acceptance, or delivery SLO is
recorded.

**Source recovery progress (2026-10-01):** the API's dedicated PostgreSQL listener
now detects established termination and half-open/probe failures, clears
readiness, bounds registration/cleanup/close, ignores stale callbacks, cancels
cooperative stalled dispatches and retries re-registration. Hosted `/ready`
requires both SQL and listener health before returning ready; `/health` stays
liveness-only. Unit/API coverage includes registration failure/timeout, close
during registration, probe error/timeout, healthy probes, stale callbacks,
recipient isolation, single ownership, shutdown and sanitized readiness/logs.
A fresh migrated regression additionally terminates only the test-owned listener
PID, verifies a new registered channel and addressed-only hint delivery, and
checks cleanup. The T3 report requires that named recovery case; this local
connection test is not hosted database failover or provider/device acceptance.

Local verification passed 78 focused unit/API cases, 197 infrastructure tests
and the 20-persona/60-selected-test T2 pack. The complete guarded fresh-PostGIS
run passed **1,042 tests with zero failures, errors or skips** and three existing
dependency deprecation warnings. Its `backend/build/live-event-recovery-t3-20261001/`
records include the actual owned-PID recovery case, migration 0052 metadata,
zero residual clones, revoked temporary `CREATEDB`, and an 81-table/8,511-row
logical restore with temporary target/dump removal. All six bounded T3 evidence
kinds are present; formal phase/deployment acceptance remains false. Documentation,
source credentials, mobile/web contracts, phase evidence, CI security and
production Compose checks pass. Engineering scope remains approximately 84%
and P0 deployment acceptance remains 0/19; this reliability repair is not a new
accepted provider or launch gate.

**Mobile recovery progress (2026-10-02):** Android and iOS now use a shared,
single-owner subscription supervisor rather than a ready-category-only effect.
Foreground, advisory network availability and security-command state control
admission. A non-secret local session generation cancels the old socket and
catch-up when credentials change or the session ends. Credential restoration is
serialized to avoid concurrently rotating the same refresh token; logout closes
hint admission before awaiting push cleanup, and late/queued restores cannot
reopen it during that cleanup. Ordinary same-session REST refresh keeps the
generation stable.

Network/rejection failures and normal socket closure trigger read-only REST
catch-up and cancellable exponential jitter (initial 0.5–1 second, capped at
15–30 seconds). Admission triggers catch-up before frame consumption. Handshake
and catch-up have ten- and fifteen-second bounds respectively; a healthy idle
socket has no artificial timeout. Cancellation propagates and obsolete callbacks
cannot apply render state. No ride, money or availability command is replayed.
Shared regressions and mutation-checked native wiring cover these boundaries;
the HINT-06 source pack in `testing.md` names the executable cases. Native device
traces, FCM/APNs delivery and hosted failover remain separate acceptance evidence.

Local verification passed 31 new focused shared regressions within the complete
235-test JVM and 186-test Android host suites, both Android debug-root compiles,
57 tests on each JS/Wasm browser target, 41 mobile script tests (including
21 source-wiring mutations), and 197 infrastructure tests. Documentation,
mobile/web API, credential hygiene, existing mobile recovery, phase evidence,
CI security and production Compose gates pass. Backend business code and schema
are unchanged; the previous 1,042-test PostGIS result belongs to the server patch,
not a new database run. Immutable mobile candidate `8f92e51` now passes its push
and PR CI workflows, including macOS native-source/test compilation and both
Release simulator application links; no native iOS/device test execution is claimed.

**Ongoing server authority progress (2026-10-02):** socket ownership is now
modular: verified mobile IDs/access deadline, fresh SQL authority shared with
REST, and an independent per-connection lifecycle. Admission, every send and the
idle monitor check exact session ownership, database expiry/revocation and
active account status without positive caching or raw bearer retention. Known
loss closes `4401`; unavailable authority closes `1013`. Refreshed credentials
must establish a replacement owner. Sends serialize per socket without blocking
other recipients; shutdown joins admission and closing owners as well as live
recipients. A retained closer survives caller cancellation. Inbound text/binary
frames cannot execute commands, and the ASGI receiver no longer races a
server-initiated close through `receive_text`'s connected-state precondition.

HINT-08 adds unit/ASGI cases for expiry, denial, lookup/accept/send/close stalls,
revoked/suspended idle connections, cancelled admission/publisher/closer,
late-accept/shutdown ownership, recipient isolation, minimized payloads and
sanitized failures. Separate migrated tests use fresh SQL sessions to commit
session revocation, account suspension and database-session expiry. The full
T3 report now requires both `LIVE_SESSION_AUTHORITY` cases; a mutation test
rejects omission of either. Transport-only listener fixtures explicitly inject
synthetic authority and are not a substitute for those database cases.

Local verification passed **106 focused backend cases**, **199 infrastructure
tests**, three mobile live-wiring regression tests and the network-guarded
**20-scenario/66-selected-test T2 pack**. The complete guarded fresh-PostGIS
regression passed **1,090 tests, zero failures/errors/skips**, with three existing
dependency deprecation warnings. The
`backend/build/live-session-authority-t3-20261002/` bundle includes both required
SQL authority cases, migration 0052, zero residual clones, revoked temporary
`CREATEDB`, and an 81-table/8,511-row logical restore with temporary target/dump
removal. All six bounded T3 evidence kinds pass while phase/deployment acceptance
remain false. Documentation, mobile/web API, credential hygiene, mobile live
wiring, phase evidence, CI security and production Compose checks pass. No new
dependency, migration, UI or payment/provider contract is introduced. Current
server commit `2d6a68b` now has passing push and PR CI, as recorded in GAP-001;
physical/hosted acceptance remains a separate verification boundary.

**Remaining acceptance boundary:** 15-second idle/five-second operation defaults
are not an approved immediate-revocation or delivery SLO. No database lock spans
network IO; revocation after a fresh read can race an already-started send, and
already buffered/sent bytes cannot be recalled. Cooperative work is cancelled;
Python cannot force-kill an adapter that suppresses cancellation forever, so
incomplete cleanup is explicitly reported. HINT-08/T4/T5 must prove physical
multi-device logout/refresh, multi-replica idle/send revocation, authority outage,
pool/load headroom and approved measured budgets. FCM/APNs, hosted failover,
staff response and deployment acceptance remain open. REST reauthorization
remains authoritative throughout. Source scope is approximately 84%; P0
deployment acceptance remains 0/19.

**Risk:** passengers and drivers miss offers, assignments, cancellations,
scheduled reminders, document decisions, or urgent support updates.

**Required closure:** create isolated Firebase projects on the no-cost Spark
scope, configure Android package/SHA data and APNs keys, restrict service
credentials, define rotation and revocation, test token replacement and invalid
registrations, localize all approved event types, connect dead-letter alerts to a
named operator, and keep polling/authoritative refresh behavior safe.

**Acceptance evidence:** controlled Android and iOS delivery matrix for
foreground/background/terminated states; permission denied/re-enabled tests;
token rotation/revocation proof; localized payload screenshots; dead-letter alert
and replay drill; measured delivery latency and loss against an approved SLO.

### GAP-010 — Accept cash and manual-transfer operations with real money

**Current gap:** the backend records cash and manually reviewed external transfer
claims, but no verified real recipient, bank/M-Wallet terms, transfer fee/limit,
statement/reference fidelity, cash custody control, reviewer roster, daily
reconciliation, real refund, accounting export, or dispute process is accepted.

**Risk:** false payment claims, misdirected funds, duplicate settlement, fraud,
unreconciled driver earnings, cash leakage, or inability to refund passengers.

**Required closure:** verify recipient ownership out of band; approve city/
operator/service capability and exact displayed instructions; run controlled
transfer submit/verify/reject and refund cases; define segregation of duties,
daily reconciliation, unresolved-claim aging, cash handoff/driver declaration,
exceptions, accounting records and customer communication. Do not advertise card
or mobile payment provider capabilities.

**Acceptance evidence:** real low-value transfer found by exact reference, amount
and currency; idempotent decision evidence; earning/payment/recipient provenance
reconciliation; rejected/corrected claim; real refund proof; cash shift close;
signed runbook and duty roster; legal/accounting approval.

### GAP-011 — Staff support, safety, paging, and emergency handling

**Current gap:** software queues, case states, overdue alerts, pager adapter,
legal holds, retention and audit exist. No staffed hours, response targets,
escalation roster, real pager, emergency-service wording, law-enforcement request
process, vulnerable-user policy, shift handoff, or controlled incident exercise is
accepted.

**Risk:** urgent reports may sit unanswered while the UI creates a false
expectation of safety assistance. Sensitive notes may be mishandled.

**Required closure:** define support versus safety scope; state clearly that the
app does not replace emergency services; assign primary/backup responders;
configure real paging; approve triage, escalation, evidence minimization,
participant communication, legal hold/release, law-enforcement and after-hours
procedures; train staff and rehearse.

**Acceptance evidence:** controlled support case and urgent safety drill from
mobile report through acknowledgement, escalation, resolution, retention/legal
review and shift handoff; measured response times; pager failover; audit/privacy
review; published emergency limitation and support contacts.

### GAP-012 — Productionize protected driver documents

**Current gap:** PDF/JPEG/PNG client selection, metadata, authorization,
encryption/scanner adapters, reviewer retrieval, retention and legal hold paths
exist and fail closed. Production private storage, independent encryption key,
scanner, malware definitions, volume backup/restore, upload proxy limits,
processor/data-region approval, and browser/iOS acceptance are absent.

**Risk:** identity and licensing files can leak, be replaced, evade scanning,
become unavailable, or outlive their legal purpose.

**Required closure:** deploy private non-public object/file storage and a private
scanner; separate keys and access roles; enforce content sniffing, bounded size,
quarantine and retrieval headers; define required documents by city; approve
retention and legal basis; test key rotation, scanner outage, malicious files,
backup/restore and verified erasure; prohibit free-text file references.

**Acceptance evidence:** security architecture review; EICAR/malformed/polyglot
tests; Android/iOS/browser upload and reviewer-download matrix; access-denial and
audit tests in production-like staging; restore and erasure report; processor,
region and retention approval.

### GAP-013 — Produce signed, store-ready mobile releases

**Current gap:** Android debug/release-verification builds and iOS simulator build
paths exist, but real signing, package/bundle ownership, app-store accounts,
production environment configuration, Firebase files, APNs entitlements,
Crashlytics symbols, store privacy declarations, rollout channels and physical-
device acceptance are open.

**Risk:** an unshippable or incorrectly configured app may talk to test services,
expose debug behavior, fail on actual hardware, or be impossible to support.

**Required closure:** secure signing keys/certificates; freeze identifiers and
versions; generate production configs without committed secrets; build passenger
and driver artifacts in trusted CI; scan/sign/notarize as applicable; test upgrade
and rollback policy; complete store metadata, privacy/data-safety forms, support
URLs, screenshots and release notes.

**Acceptance evidence:** signed AAB/APK and iOS archive/TestFlight builds mapped
to the release commit; verification of API/map/Firebase endpoints; representative
OS/device matrix; install/upgrade/uninstall tests; crash symbolication; store
pre-review or internal-track acceptance; owner sign-off for both roles.

**Protected-storage source follow-up (2026-10-02):** Android now uses one
encrypted envelope, validated legacy migration, checked commits and explicit
sanitized errors instead of destructive corruption recovery. A preference-
facility-shared lock/uncertainty fence prevents a replacement Activity/store
from trusting process memory mutated by an unsuccessful write. Local T1 evidence
is 22 adapter cases within 208 Android host tests, 235 freshly rerun JVM tests,
both debug-role compiles, 204 infrastructure and 41 mobile-script tests. This
is also GAP-001/GAP-016 prerequisite work, not signed/native acceptance.
The ordered storage pack in `testing.md` and `testing_execution_map.md` strengthens
T4-AND-001/002/003 for both Android products and roles. Catalog revision
`2026-10-02` has a new exact-byte hash with LF checkout normalization; old
bindings cannot accept the expanded observations. Mutation tests reject removal
of required observations, device/product/role authority, severity and case IDs.
All 56 template cases remain `NOT_STARTED`, with no phase/deployment acceptance.
Keystore, process death, disk failure, upgrade, logout/recovery, EN/FR/AR usability
and real backend revocation must be evidenced before staff/field/pilot promotion.
No new dependency, platform capability, business policy or schema was added.

### GAP-014 — Add web CI, secure hosting, and browser E2E acceptance


**Current gap:** web CI and release packaging pass for the immutable candidates
recorded in GAP-001, but no full browser E2E suite has
run against the approved support matrix. Production hosting, exact CSP/TLS/cache
headers, cookie/CORS/CSRF verification, accessibility, RTL, and protected-
document browser flow remain unaccepted.

**Risk:** untested web code can break privileged operations, weaken browser
security boundaries, expose source/maps or sensitive content, and block city
launch administration.

**Required closure:** make the chosen JS/Wasm distribution strategy explicit;
add both compile targets and web tests to CI; add Playwright or equivalent E2E
for applicant and operations critical paths; deploy with strict CSP and secure
headers; verify same-site cookies, CSRF rotation, allowed origins, no-store
sensitive responses, cache invalidation and error redaction; disable source maps
or protect them according to policy.

**Acceptance evidence:** passing clean-commit web CI; Chrome/Firefox/Safari or an
approved support matrix; automated auth/MFA, scope, city lifecycle, document,
pricing, route, payment, case and audit journeys; CSP/header scan; accessibility
and RTL report; production-like hosted acceptance.

**Implementation progress (2026-09-09):** CI now compiles and launches existing
JavaScript and Wasm browser tests, builds the Compose compatibility distribution,
and packages it through `package_web_release.py`. The packager rejects missing or
remote boot resources and inline scripts, enforces reviewed initial raw bundle
ceilings, excludes `.map` files, emits SHA-256/size records, and records a hosting
header template requiring exact API/WebSocket restriction. The 2026-09-09 local
production package passed with 81 files and 33,777,513 bytes excluding three
source maps; its manifest deliberately leaves `deployment_accepted=false` until
hosted acceptance. Six dependency-free runtime scenarios now exercise the static
compatibility loader and its fail-closed/header-scoping behavior in the web CI
job. On 2026-09-09 the Gradle JS and Wasm browser suites both passed on the
Windows verification host; remote CI, full critical-journey E2E, Firefox/Safari
or an approved support matrix, and hosted acceptance remain required. An earlier
in-app Wasm browser smoke test rendered both
operations and applicant entry surfaces, found and fixed a nested-scroll
infinite-height exception on the narrow applicant layout, and then passed the
applicant route at 390 px and 1280 px without horizontal overflow or new runtime
warnings/errors. The production compatibility output is still large: the current
fallback JavaScript is 6,104,171 bytes (about 5.82 MiB), the application Wasm is
6,818,646 bytes, and the Skiko Wasm runtime is 8,652,729 bytes before transfer
compression. The JavaScript ceiling was reviewed at 6,250,000 bytes, leaving
2.39% headroom over the measured candidate rather than weakening the gate
broadly. The Wasm and total-release ceilings remain unchanged. These ceilings
prevent silent growth; measured startup on target networks and further
optimization remain acceptance work.

The packaged compatibility release now also has a bounded real-browser boot
collector wired into CI. It serves only a loopback test origin, verifies exact
applicant/operations client identity, exercises supported, upgrade-required and
preflight-failure branches, requires exactly one JS/Wasm runtime branch only
when boot is authorized, and fails closed unless each scenario retains a valid
screenshot. A local 2026-09-09 run passed all eight scenarios in Chrome 152 and
Firefox 155 with eight screenshots. Safari, authenticated and privileged
journeys, accessibility/RTL, console/source-map review, hosted headers and an
independently firewalled browser-egress environment remain missing. The report
therefore covers no complete T4 catalog case and cannot accept T4 or deployment.

### GAP-015 — Connect monitoring, alerting, crash reporting, and on-call

**Current gap:** readiness/metrics endpoints, aggregate and fixed-owner queue
metrics, 21 Prometheus rules, worker heartbeats, bounded structured API/worker
logs, a hardened self-hosted Prometheus/Alertmanager/Loki/Alloy/Grafana overlay,
file-provisioned operations and log dashboards, and Crashlytics boundaries exist.
Dead-letter alerts preserve one closed operational owner label. No target
environment runs and accepts this stack or routes to a real receiver; there is no
hosted/populated metric or log dashboard acceptance, pager, on-call schedule,
SLO, synthetic check, mobile crash project, symbol upload, capacity/restore
result, or alert tuning.

**Implemented progress (2026-09-05):** outbox snapshots retain the existing
aggregate gauges and additionally map every classified topic to the closed
`dispatch_operations`, `scheduling_operations`, or `driver_compliance` owner.
Unknown stored topics fail closed into `unclassified`; topic, resource, payload,
authorization and user identifiers never become metric labels. The committed
dead-letter rule groups by owner and its offline validator rejects aggregate-only
regressions, private dynamic dimensions and ownerless annotations. Unit tests
cover aggregation, stable zero buckets, privacy and rule mutations. A real
PostGIS provider-failure/restart case proves that a pending city-authorization
notice appears only under `driver_compliance` and clears after successful
delivery. This is source-level attribution, not proof that a collector scraped
it or that a human received and acknowledged an alert.

The optional production overlay now gives API and worker fixed aliases on one
internal-only network, scrapes both authenticated endpoints with a Docker-secret
bearer token, loads the 26 reviewed rules, and connects only to its internal
Alertmanager. Prometheus has no external network and defensively removes private
identifier labels before alert delivery. Alertmanager alone receives a dedicated
outbound bridge for HTTPS delivery and has exact routes for dispatch, scheduling and
driver-compliance owners, sends unsupported/non-owner alerts to platform duty,
loads all HTTPS webhook URLs from secret files, bounds batches and sends resolved
notifications. Images must be digest pinned; UIs bind only to host loopback.
Offline mutation tests, merged-Compose validation and the real Prometheus 3.14.0/
Alertmanager 0.33.1 parsers pass locally. Both hardened containers also became
ready with disposable volumes and were removed cleanly. This implements a
deployment path, not its target uptime, capacity, receiver delivery or staffed
response evidence.

The same overlay now runs Grafana as its native fixed UID with a read-only root,
separate persistent state and loopback-only UI. It reads a unique administrator
password from a Docker secret, disables anonymous access/signup/telemetry/update
traffic/Grafana-managed alerting, and can reach only internal Prometheus. One
immutable datasource and one immutable 26-panel operations dashboard are
provisioned from repository files. An offline validator allowlists every metric
and grouping label and mutation tests reject private identifiers, unknown metrics,
panel removal, external datasource URLs, anonymous access and dashboard egress.
The pinned Grafana 13.2.1 image became healthy with these exact hardening and
provisioning settings in the disposable runtime validator, which removed its
container and volume. This is packaging evidence only: it contains no hosted
series, named staff access, credential-rotation drill or operator diagnosis.

The application image now has fixed UID/GID `2000` and can write its allowlisted
JSON events to separate API/worker named volumes with mode `0640`, 10 MiB default
rotation and five backups. Alloy runs unprivileged with only group-read access,
mounts those volumes read-only, has no Docker socket/host-log/remote-config or
egress authority, rejects malformed and over-16-KiB lines, and indexes only the
fixed service label. Internal unauthenticated Loki stores TSDB v13 data in a
private volume and enforces a 30-day ingest/query/compactor-retention boundary.
The immutable three-panel log dashboard uses only the internal Loki datasource.
Prometheus also scrapes Loki/Alloy and alerts on any of the four required targets
being down, collector rejection, or write retries/drops. The operations dashboard
health panel covers all four targets.

Official Loki and Alloy parsers, Linux UID/GID/mode/rotation checks, real HTTP
readiness, Grafana provisioning, and a disposable API+worker ingestion query all
pass locally with the pinned images. The smoke proves exactly two safe streams
arrive and malformed/oversized fixtures do not. Immutable `de69829a` CI passed
the mirrored parser, provisioning, and ingestion path. This is source/candidate
evidence, not hosted retention, disk-pressure, restart-position, backup/restore, staff-
access, diagnosis, or on-call acceptance. The single-host file topology is also
limited to one API and one worker; national replicas require per-replica volumes
and collectors or another reviewed isolated transport.

**Risk:** outages, stuck workers, dead-letter growth, migration failure, payment
backlog, urgent cases and app crashes can remain invisible.

**Required closure:** define service and business SLOs; deploy and accept private
metric/log collection; validate rotation, read-position restart, 30-day deletion,
disk-pressure behavior, backup/restore, per-replica collection, and the HA/object-
storage transition threshold; validate the existing service/worker/outbox/log
dashboards with real staging series and create database, routing, push, payment
queue, case and mobile dashboards; route alerts to primary/backup duty;
configure Crashlytics without enabling unrelated metered Firebase products;
write runbooks and tune alerts through failure injection.

**Acceptance evidence:** monitored staging/production targets; authenticated
dashboard access/privacy/diagnosis and credential-rotation records; synthetic journey;
forced API/worker/database/routing/push failure alerts; acknowledgement and
escalation timings; dead-letter and overdue-case alert drills; symbolicated test
crash; dashboard/privacy review; on-call handoff record.

### GAP-016 — Complete independent security and supply-chain assurance

**Current gap:** source protections, Python `pip-audit`, pull-request dependency
review, resolved Gradle graph submission, a blocking backend-image scan, an image
SBOM/provenance definition, and a repository threat/control/test baseline passed
in immutable `de69829a` CI. Repository Dependabot currently reports 20 unresolved
alerts (8 high, 9 medium, 3 low), predominantly in generated Kotlin JS/Wasm lock
files. There is no accepted independent threat-model review, abuse-case workshop,
penetration test, DAST, complete JavaScript/Gradle current-tree vulnerability
gate, mobile/web artifact SBOM, secret rotation drill, code-signing provenance,
or remediation SLA.

**Risk:** authorization flaws, cross-scope leakage, browser attacks, dependency
compromise, insecure images, and untracked critical vulnerabilities.

**Required closure:** threat-model mobile/web/API/workers/database/providers and
staff misuse; run SAST, DAST, secret, container and all-ecosystem dependency
scans; generate SBOMs; review auth/MFA/CSRF/IDOR/scope/document/payment/location
boundaries; commission a penetration test before public launch; define severity
SLAs and disclosure/incident handling.

**Acceptance evidence:** approved threat model; clean or formally risk-accepted
scan reports; artifact SBOMs and provenance; penetration-test report with retest;
credential rotation drill; no unresolved critical/high findings unless the
security owner records bounded compensating controls and an expiry date.

**Implementation progress (2026-09-01):** `threat_model.md` now inventories ten
security objectives, ten trust boundaries, protected assets, threat actors, 35
identity/authorization/ride/payment/data/platform threats, required controls,
11 phased security test packs, test-data rules, stop conditions, evidence fields
and review triggers. Cross-market account containment now fails closed unless one
platform principal covers every associated market. CI pins every action by commit,
rejects new high/critical dependencies on pull requests, submits the resolved
Gradle graph on trusted pushes, generates an SPDX JSON SBOM from the built backend
image, binds its hash into source-candidate evidence, and makes Trivy high/critical
OS/library findings blocking, including unfixed findings. A standard-library
validator and four regressions prevent those controls from becoming tag-based,
non-blocking, or detached from provenance. This remains source configuration—not
a passed remote report, complete all-artifact scan/SBOM set, independent review,
penetration retest, deployed secret drill, or security-owner acceptance.

**Dependency-audit refresh (2026-10-01):** the location candidate's immutable
CI audit rejected PyJWT 2.14.0 (`CVE-2026-101918`) and urllib3 2.7.0
(`CVE-2026-97687`, `CVE-2026-97688`, `CVE-2026-97689`). Both runtime and
development locks now pin PyJWT 2.15.1 and urllib3 2.8.0 with PyPI release hashes;
the runtime hash-enforced install, `pip check`, and runtime audit passed. Fourteen
new authentication regressions verify nested signed payloads and non-numeric
time claims fail as `InvalidAccessToken` for both mobile and operations tokens.
Local backend unit/API verification passed 860 tests (173 existing warnings),
and the infrastructure suite passed 194 tests. The monitoring failure annotation
now depends on the monitoring step's own failure, avoiding a missing-log error
after an unrelated earlier failure. No vulnerability ignore or weakening of
the blocking audit was introduced. These local results do not clear existing
default-branch alerts, all-artifact scans, independent review or GAP-016.
**Test-toolchain remediation (2026-10-01):** the separate development-lock audit
identified pytest 8.4.2 (`PYSEC-2026-1845`, fixed in 9.0.3), while pytest-asyncio
0.26.0 constrained pytest below 9. The reviewed pair is now pytest 9.0.3 and
pytest-asyncio 1.4.0, with verified PyPI artifact hashes and explicit
function-scoped fixture and test loops. Hash-enforced installation and
`pip check` passed. Separate local runtime/development audits report no known
vulnerabilities; Windows intentionally does not resolve the Linux-only wheel
supplement. Linux CI now audits the development lock and supplement in a separate
blocking step, alongside the existing runtime audit. Mutation tests reject
removed, commented, duplicated, skipped, pipeline-bypassed and non-blocking audit
steps or backend jobs.

The upgraded runner passed 20 simulated personas/60 exact selected tests, the
196-test infrastructure suite, and the full fresh-PostGIS run: **1,011 tests,
zero failures/errors/skips**, with three existing Starlette deprecation warnings.
The local evidence bundle at `backend/build/pytest9-t3-20261001/` confirms
PostgreSQL 16.14/PostGIS 3.5.3 at migration 0052, all named concurrency/worker/
reconciliation cases, zero residual clones, revoked temporary `CREATEDB`, and a
guarded restore matching 81 tables and 8,511 aggregate rows with target/dump
cleanup. All six T3 evidence kinds are present; engineering sign-off, clean
immutable CI acceptance and ordered promotion remain separate. No audit ignore,
business-policy or schema change was introduced. These dated local results do
not clear browser/native/container dependencies, existing default-branch alerts,
independent security review, provider acceptance or GAP-016. The weighted source
estimate remains approximately 84%; all 19 P0 deployment gates remain open.

### GAP-017 — Complete privacy, terms, and regulatory compliance

**Current gap:** data minimization, scoped access, aggregate suppression,
retention workers and legal holds exist technically. There is no approved privacy
notice, terms for passengers/drivers/applicants, data inventory, lawful-basis and
retention schedule, DPIA, processor register, cross-border assessment, cookie
policy, consent record design, or data-subject request process.

**Risk:** unlawful collection/use of identity, location, ride, payment and safety
data; inability to answer access/deletion/correction requests; misleading users.

**Required closure:** obtain qualified Moroccan legal/privacy review; map every
data field/event/recipient; define purpose, legal basis, retention and access;
complete DPIA for location, matching, driver documents, safety and analytics;
approve processors/regions/contracts; publish localized terms/notices; create
verified access, correction, deletion/restriction and objection procedures;
reconcile legal holds and backups.

**Acceptance evidence:** signed data inventory, DPIA, processor register and
retention schedule; versioned localized notices/terms; staff procedure and test
request; consent/version records where required; verified deletion/hold/backup
behavior; named privacy contact.

### GAP-018 — Prove performance, capacity, availability, and failover

**Current gap:** bounded GET smoke tooling, a synthetic passenger request/cancel
HTTP workload, leases, Postgres hints, health checks and a multi-role Compose
design exist. There is no approved workload model, concurrency target,
peak-city dataset, full multi-role/payment/scheduling load test,
multi-replica soak, database failover, routing/provider degradation, autoscaling,
capacity budget, or measured SLO.

Live-ride hardening now uses a consistent ride-before-offer/driver lock order for
acceptance, decline, cancellation and expiry, with post-wait ORM refresh. Driver
transition/completion commands refresh their profile as well as the ride; dispatch
cannot reopen an operational ride. Eleven migrated synthetic cases cover seven
observed command lock races, expiry-worker skip/retry and three active-state
dispatch rejections. These improve local correctness evidence, but are not a
workload model or multi-process/load acceptance. Administrative revocation,
mixed scheduling/live workloads and provider delays
remain explicit scope for the deployment concurrency matrix in `testing.md`.

Migration `20260903_0048` adds the missing database one-active-ride-per-driver
backstop. Two observed competing-driver/ride races and both scheduled/immediate
assignment orders now have one-winner evidence. Four direct-write state cases
prove the index and terminal slot release; downgrade/preflight/reapply testing
proves duplicate data is refused without automatic repair. The mixed fixture
deliberately supplies a stale outstanding offer while the driver is available;
it does not claim this overlap is the normal sequential matching path. Index-build
duration/locking on realistic data, independent-process contention, and the full
administrative/financial race matrix remain unaccepted.
The Alembic environment now uses a fail-fast, database-scoped transaction advisory
lock before version reads/DDL; generated offline SQL uses the same guard.
Six unit/source checks and seven PostgreSQL cases cover actual CLI contention,
commit/rollback/disconnect release, execution of the offline guard, and retry after
termination of a lock-owning process. Keep the documented single production
migration job: this cooperative guard does not protect bypassing manual DDL,
bound schema-lock/build duration, or prove hosted orchestration/traffic safety.
The chain must remain one transaction; nontransactional future migrations require
a new reviewed lock lifetime. Hosted duplicate-job/startup, failover and maintenance
acceptance remain open.

Per-lock and per-statement migration timeouts are now implemented with nonzero
validated limits, transaction-local online/offline settings and fixed CLI
cancellation diagnostics. Twenty-one unit cases, one migration-only Compose
configuration check and four PostgreSQL/CLI cases cover configuration refusal,
blocked index upgrade rollback, ownership release/retry, statement cancellation
and settings restoration. This narrows unbounded database-wait risk; it does not
bound connection setup, idle Python work or the sum of a whole migration chain.
An outer deployment deadline, representative timeout calibration, hosted traffic
compatibility and reviewed blocker/retry handling remain required.

The new modular `operations/workload/` runner registers independent synthetic
passengers through ordinary APIs, checks quote/create/replay/restore/cancel
journeys, and emits aggregate per-step latency/failure evidence with deadlines
and bounded recovery. Real CLI-to-Uvicorn/PostGIS tests verify four cancellation
journeys and registration throttling before ride writes. The concurrent test
exposed candidate-set overlocking; dispatch now locks/rechecks individual ranked
candidates, leaving transiently locked/changed supply for bounded worker retry.
Three held-transaction tests prove distinct-driver selection, retry after release
and overall-deadline exhaustion. No ranking weights or eligibility policies were
relaxed. See [testing_workloads.md](testing_workloads.md) for guards, commands,
measurement limits and LOAD-01–12 progression. This is source/local write-path
evidence, not open-loop capacity, national peak demand or hosted fault acceptance.
The next slice adds `passenger_request_cancel_open_loop_v1`: after normal account
admission it releases a bounded constant-rate schedule independently of response
time, caps in-flight work by the passenger actor pool, measures arrival lag and
backpressure separately from HTTP/journey latency, and stops new release after a
failed invariant. Unit tests plus a real child CLI/Uvicorn/PostGIS case reconcile
four arrivals through cancelled rides, offers, idempotency, events and outbox rows.
This closes the missing open-loop scheduling primitive only; there is still no
approved peak mix, representative dataset, resource/cost curve, multi-role burst,
multi-replica soak, provider/database failure or accepted capacity envelope.
The follow-up adds a strict target-independent profile and four-phase executor.
It requires ordered WARMUP/STEADY/BURST/RECOVERY phases, prevalidates the full
plan, caps aggregate arrivals/runtime, records a canonical profile digest and
stops before later phases after failure. Mutation tests and a second child CLI/
Uvicorn/PostGIS case execute and reconcile all four phases. The repository
template is deliberately DRAFT: textual approval fields and confirmation flags
are not owner sign-off, and no pilot/national profile or threshold is approved.
Each profile now carries fixed operational thresholds and monitoring cadence.
An optional protected Prometheus sampler records 22 aggregate application,
worker, outbox, log-delivery, PostgreSQL and per-process SQLAlchemy-pool signals
for every phase; it rejects labels,
redirects, malformed/multiple/non-finite results and oversized bodies, and an
incomplete or over-threshold phase prevents later phases. Local CLI/PostGIS tests
use an explicit no-monitoring harness mode and therefore make no telemetry claim.
The authenticated process endpoints now collect fixed current-database snapshot
availability, connection use/limit, active connections, waiting locks and
deadlocks; a real isolated-PostGIS case proves the application role can read the
aggregate statement. They also publish fixed, unlabelled per-process pool
availability, configured size, checked-in, checked-out and overflow gauges, a
cumulative checkout-wait histogram and timeout counter.
Production configuration explicitly bounds pool size, overflow and checkout
timeout for API and worker; operators must keep `(size + overflow) * replicas`
within the managed database connection budget with migration and operations
reserve. Eight immutable database/pool alert rules and nine dashboard panels
cover snapshot and pool availability, utilization, checked-out connections,
overflow, checkout-wait p95, checkout timeouts, waiters and deadlocks. A real
isolated-PostGIS exhaustion case proves a size-one/no-overflow pool records one
bounded timeout while its only connection is held. No hosted run has yet supplied
or accepted these series, and host CPU/memory/disk/network, query
plans, provider latency and client crash metrics remain outside this sampler and
open for T5 acceptance.
The paired cash runner now traverses actual driver acceptance, start, completion,
cash settlement, receipt and earnings with exact monetary conservation. Three
real-HTTP fixture variants cover zero fees, a flat driver-funded fee and a
percentage passenger surcharge. Two further cases inject HTTP 503 after a real
completion/settlement commit, preserving pending-versus-settled facts and exactly
one earning rather than retrying with a new key or inventing cleanup success.
Independent supply timing, realistic trips, driver decline/expiry/no-show,
manual-transfer/refund, scheduled/fixed-route and provider/load/soak acceptance
are still required. These are synthetic payment records, not real cash custody
or operator-driver payout evidence. Scheduled fallback still requires an
immediately obtainable offer; deferred fallback semantics need separate review.

Current protected-window enforcement now spans scheduling and immediate rides.
A shared correlated range predicate excludes current active commitments during
candidate discovery, after candidate locking and again during live-offer
acceptance. Scheduled acceptance takes the reciprocal driver lock and refuses a
current-window commitment when an active live ride won first. Seven PostGIS cases
cover half-open boundaries, cancellation release, candidate/stale-offer behavior,
both observed-wait acceptance orderings and `SKIP LOCKED`; three authenticated
ASGI cases prove both `409` boundaries and allowed immediate work outside the
current range. All 28 focused acceptance/protection cases passed locally on
2026-09-04. The pack is `PROTECT-01`–`PROTECT-10` in `testing.md`.

This is partial closure only. There is no approved conservative duration for an
immediate ride accepted shortly before a future protected window, so its eventual
intrusion is not yet prevented or measured. Independent processes, clock skew,
process loss, device state and controlled-road calibration also remain open and
must precede pilot scheduling acceptance.

Global account suspension is now serialized with new assignment commit points.
The shared authority module treats only `users.status=ACTIVE` as eligible,
filters suspended users during matching/scheduled offering, takes `FOR SHARE`
after the driver lock for immediate acceptance, scheduled acceptance and handoff,
and uses `FOR UPDATE` for both administration suspension surfaces. Seven unit
cases cover the closed status/SQL-lock contract. Six fresh-PostGIS cases cover a
suspended candidate, a stale scheduled offer, and both observed-wait winner orders
for immediate acceptance and scheduled handoff. This is the account-status subset
of `RACE-07`, not full closure: credential/vehicle/authorization/configuration
change races, session-only revocation semantics under separate API processes,
active-ride incident handling, load/failover and device behavior remain open.

The location subset now has two additional observed-wait PostGIS cases
(`test_scheduled_location_authority.py`, passed 2026-09-05). A valid boundary
crossing committed first causes the waiting handoff to use the newer observation
and produce explicit unfulfilled/no-supply. Handoff committed first preserves its
accepted ride while the next location is recorded in `EN_ROUTE`. Each checks the
commitment, driver, ride, passenger notification and outbox state. The combined
account/location pack passes 15 cases. This narrows `RACE-07`; independent API
and worker processes, simultaneous configuration changes, physical-device
location quality and field readiness remain open in the testing map.

The city-authorization lifecycle gap found on 2026-09-05 now has a dedicated
scoped operations API and a modular console review control. Suspension,
revocation and reinstatement use recent MFA, closed reason codes, application
versions, scope-checked idempotent replay and atomic audit history. Reinstatement
requires current eligibility, preserves expiry and refuses revoked authorization
or another active application. Approval and reinstatement share the driver lock
before checking for duplicate city authority. The original application and
committed ride history remain intact; nested authorization status is current.

All 33 focused cases pass: 17 policy/input cases, nine lifecycle/handoff cases,
four actual MFA/HTTP/replay/rollback cases, and three approval-race/cross-city
cases. All 33 are also included in the passing 992-test full regression; the
preceding 956-test generated report remains at
`backend/build/security-incident-full-tests.xml`. The console compiles and its
56 model tests pass in both JS and Wasm browser tasks; the web contract gate
covers 109 calls. This closes the missing source
command surface, but independent-process races, additional
credential/configuration races, durable
provider/device notification acceptance, explicit acknowledgment/appeal semantics, browser accessibility and staffed field
rehearsal remain required. Local fixtures do not establish city launch authority.

The applicant display also no longer treats every authorization record as
active/verified: mobile and web share localized recorded-status labels, supplied
expiry and a server-eligibility/refresh notice. Two shared mapping tests and both
Android role compiles pass, along with the full 178-test shared suite and 47 tests
per JS/Wasm browser target. EN/FR/AR catalogs contain 610 matching keys. This
closes the misleading unconditional status label, not freshness while offline,
rendered accessibility or reliable delivery/acknowledgment of restrictions.

Authorization changes now atomically create a driver-owned persistent inbox row
and a classified outbox event. Delivery derives the recipient from the current
authorization and driver records and emits only a status-neutral authorization-ID
refresh hint; mobile reloads all backend-authorized state and localizes the generic
notice. Real-MFA replay and post-outbox fault tests prove exactly-once source rows
and full rollback/retry. This closes the missing producer, not provider/device
delivery, explicit acknowledgment, appeals, unreachable-driver escalation or
field comprehension.

A migrated worker-recovery test now commits a real suspension, forces push
failure, verifies a sanitized retry with no retained lease, then creates a new
processor instance and delivers the same minimized hint. The persistent notice
remains singular and the event records two attempts before delivery. This proves
database-backed recovery across processor lifetimes, not independent operating-
system processes, worker death, real FCM/APNs or device visibility.

The next case crosses that first boundary: a real child Python process claims and
leases the authorization event, is forcibly terminated before delivery, and a
separate replacement process reclaims the stale lease and delivers once. The
database records two attempts, clears the lease and retains one inbox notice;
captured child output is checked for database-URL leakage and the push hint for
recipient/reason/status leakage. This still does not prove independently deployed
API and worker services, container/process orchestration, real FCM/APNs, hosted
metric scraping/alert routing, staff response or device visibility.

Immediate city restrictions now have ten additional PostGIS cases: acceptance
in both lock orders, uncommitted restriction/skip-locked retry, committed
restriction exclusion, and offer-first/restriction-second stale acceptance.
Two further observed-wait cases reproduced and fixed a dispatch assertion after
global suspension wins between discovery and final selection; dispatch now uses
another eligible candidate or safely defers for retry. Selection only becomes
final after guards and a fresh post-lock eligibility query. The combined
30-case focused pack passes. Independent HTTP/process, statement-snapshot timing,
configuration/credential changes and field evidence remain required; passing
these tests is not operational closure of GAP-018.

**Risk:** request latency, offer expiry, lock contention, duplicate work, pool
exhaustion or cascading failure under real demand.

**Required closure:** model pilot and national peak load; seed representative
geography/history without personal data; test critical read/write journeys and
all eight worker loops; run multi-replica soak and chaos scenarios; inspect
PostGIS plans/indexes, locks, queues and pools; define capacity headroom and
degradation behavior; test database/provider failover and emergency city pause.

**Acceptance evidence:** approved workload and SLO; reproducible load scripts;
results with p50/p95/p99, error, queue and resource metrics; no unbounded privacy
logging; failover/restore timings; bottleneck fixes; capacity and cost forecast;
operations sign-off.

### GAP-019 — Run a complete controlled city acceptance and rollback exercise

**Current gap:** automated domain tests prove isolated behavior, not the complete
human and provider workflow. No real city has executed recruitment through ride,
money, support/safety, analytics, pause and closeout.

**Risk:** individually correct components fail at handoffs, leaving passengers,
drivers, money, or cases in inconsistent states.

**Required closure:** after GAP-001 through GAP-018 are satisfied for the selected
scope, execute a staged acceptance with named passenger, licensed driver,
reviewer, dispatcher/support, finance and market-admin roles. Cover application
and documents, authorization, availability, immediate and scheduled/fixed-route
rides where enabled, decline/expiry, cancellation, cash and transfer, refund,
support/safety, notification, offline recovery, emergency pause, analytics,
backup/restore and release rollback.

**Acceptance evidence:** signed scenario record linked to immutable build and
configuration versions; reconciled ride/payment/earning/audit facts; measured
SLOs; defect and residual-risk register; successful pause/recovery/rollback;
formal go/no-go decision and bounded pilot plan.

**Implementation progress (2026-09-08):** the T0–T10 execution map now has a
machine-readable phase catalog, an empty non-claiming evidence-index template and
a standard-library validator. It requires ordered acceptance, exact phase
evidence/sign-off functions, immutable candidate hashes, defect disposition and
all 19 P0 closure references before T8. It rejects public users before T9, live
money before T8, unsafe field failure injection and real-user evidence in local
phases. This prevents a local or synthetic report from being relabeled as city
acceptance; no controlled city exercise has yet occurred.

**Implementation progress (2026-09-09):** T2 now has a strict executable
simulated-persona catalog covering 20 stable scenarios with 60 exact unit-test
nodes. The local run passed without failures, errors, or skips. CI executes it,
retains its JSON/JUnit records, and binds both to backend candidate evidence. The
runner has no target URL, provider credential, real-user, persistent-data, or
live-money mode and always reports T2/deployment acceptance false. Durable
database and money reconciliation, full adversarial review, data-minimization
evidence, security sign-off, T3 onward, and the real controlled-city exercise
remain open.

## 6. P1 — required before scaled public service

### GAP-020 — Add safe account verification and recovery

**Current gap:** migration `20260902_0046` and the mobile API now implement
expiring one-time offline recovery codes, generic rate-limited password reset,
account-wide session/push revocation, password change, notifications, and a
localized signed-out Android/iOS reset form. Recovery-code creation is available
only after password re-authentication and staff identities are excluded. Both
mobile account screens now create and display replacement codes once, warn the
user to save them, require a saved-all-codes acknowledgement before clearing the
bundle from render state, list/revoke sessions, and change the password. A
reviewed platform save/export path and physical-device secret lifecycle are not
yet accepted. Verified
email/phone ownership, delivery-based reset, compromised-account
support recovery, and production notification evidence remain absent. An email
or phone supplied at registration is still not proof that the user controls it.

**Risk:** users can be permanently locked out, contact data can be false, and an
unsafe manual recovery process can enable account takeover.

**Required closure:** device-test and approve the one-time recovery-code save/
acknowledgement interaction and decide whether a protected platform export is
needed; select a no-cost/sustainable contact-verification channel and policy without
assuming Firebase phone authentication; define compromised-account and
high-assurance driver recovery without weakening the separate staff-MFA recovery
procedure; prove enumeration/timing, notification, redaction and provider-outage
behavior in production-like staging.

**Implementation progress (2026-09-02):** eight independent 100-bit codes are
shown once by the backend, stored only as domain-separated SHA-256 digests,
expire after 180 days, rotate as one set, and are consumed atomically. A valid
reset deletes the complete set and revokes mobile sessions, operations sessions,
and push registrations. Invalid, expired, replayed, absent-account, suspended,
and staff-account attempts return the same accepted payload. Fresh-PostGIS tests
cover expiry, replay, staff exclusion, generic responses and all-session/device
revocation. Shared UI tests prove the acknowledgment gate starts disabled and
clears the codes from render state only after confirmation; Android/iOS roots
handle the same callback and do not automatically use the clipboard. This is
partial source closure, not a verified-contact recovery
system or deployment acceptance.

**Acceptance evidence:** end-to-end delivery tests, expired/replayed/rate-limited
negative tests, session revocation, enumeration review, localized UX, provider
outage behavior, support identity-proofing runbook and security approval.

### GAP-021 — Implement account lifecycle and privacy-right self-service

**Current gap:** backend APIs and both mobile account screens now list up to 100
active sessions, identify the current session, confirm/revoke an owned session
and its bound push registration, and change a password after re-authentication
while revoking all access. No complete user
account deletion, personal-data export, correction request, or processing
restriction workflow was found.

**Risk:** the operator cannot fulfill user rights consistently; stolen sessions
remain difficult for users to identify and revoke.

**Required closure:** define backend-authoritative workflows for export,
correction and deletion/anonymization; preserve legally required financial/audit
facts without retaining unnecessary identifiers; respect legal holds; add
step-up/re-authentication and delay/cancel safeguards; device-test session/
password controls including process death and stale sessions; track request
deadlines and operator actions.

**Acceptance evidence:** approved data map; automated hold/non-hold deletion and
export authorization tests; readable export sample; all-device revocation test;
backup-expiry confirmation; completed synthetic data-subject request with audit.

### GAP-022 — Complete staff-grant administration and dual-control UX

**Current gap:** scoped staff-grant maker-checker is implemented in source. The
operations console lists active grants and a durable request queue. Create and
revoke reviews derive exact scope, display the reviewed snapshot, require typed
confirmation, submit idempotently, and do not replay after MFA step-up. The maker
may cancel; the target cannot decide; a distinct authorized administrator may
approve or reject with an independent reason and expected version. Revocation is
non-effective while pending.

Migration `20260907_0049` stores pending/terminal state, maker, checker, target,
scope, source/result grants, reasons, timestamps and optimistic version. Partial
unique indexes prevent equivalent pending creates/revokes. The backend requires
recent MFA, locks the market, revalidates the deciding administrator's live
authority and reviewed state, and applies the decision and grant mutation in one
transaction. Staging/production reject direct mutations. Platform-admin
revocation cannot leave fewer than two active administrators; expiring platform
authority requires two longer-lived successors. A bounded audited offline command
creates only the second and third initial quorum members, then closes.

This remains partial deployment closure. There is no approved authoritative
staff roster, joiner/mover/leaver source, recertification cadence/reminder,
break-glass custody process, hosted accessibility acceptance, or production-like
staff/recovery drill. Other sensitive configuration and financial commands do
not yet all use the same maker-checker state machine.

**Risk:** without roster and human-process controls, technically separated
accounts can still be stale, shared, improperly approved, or unavailable during
an incident; other high-impact command families still permit one-account action.

**Required closure:** approve the authoritative roster, role owner,
recertification cadence, reminders, leaver deadline and break-glass custody;
identify which non-grant commands also require independent approval; then exercise
joiner, mover, leaver, expiry, concurrent decisions, rejection, quorum bootstrap,
last-admin refusal and emergency recovery in production-like staging with named
staff and accessible supported browsers.

**Implementation progress (2026-09-07):** four real-PostGIS scenarios cover
request/replay, maker rejection, independent approval, stale decision, approved
revocation, rejection, requester-only cancellation, changed target, initial
quorum closure, direct last-admin refusal and expiry continuity. Migration
downgrade/re-upgrade passed. Focused backend unit/API/contract tests passed, both
JS and Wasm browser tasks passed with 57 tests each, and the web/backend source
contract covers 112 expanded HTTP operations. The complete fresh-PostGIS backend
regression then passed all 992 tests at migration 0052 with no failures, errors or
skips. This is local dirty-workspace
source evidence, not accessibility, hosted MFA/CSP, authoritative-roster or
staff-rehearsal acceptance.

**Acceptance evidence:** negative scope/self/duplicate/concurrency/last-admin and
expiry tests; recent-MFA and independent-approver proof; keyboard/screen-reader
confirmation acceptance in supported browsers; audited authoritative-roster
linkage; joiner/mover/leaver, recertification and break-glass exercises.

### GAP-023 — Decide and implement passenger-driver communication

**Current gap:** a minimal privacy-preserving approach is now implemented in
source. During assigned active ride states, passengers may send only
`PASSENGER_AT_PICKUP`, `PASSENGER_NEEDS_MORE_TIME`, or
`PASSENGER_CANNOT_FIND_DRIVER`; drivers may send only `DRIVER_ON_MY_WAY`,
`DRIVER_AT_PICKUP`, or `DRIVER_CANNOT_FIND_PASSENGER`. There is deliberately no free text, masked
calling, personal-number exposure, or participant transcript. Real device
delivery, pickup usefulness, retention/erasure, accessibility, abuse escalation,
support ownership, and emergency-limitation comprehension remain unaccepted.

**Risk:** pickup coordination fails, while improvised direct contact exposes
personal data and creates harassment, retention and support risk. A constrained
signal can also be delayed, misunderstood, repeatedly sent, or mistaken for an
emergency channel unless field behavior and failure handling are accepted.

**Implemented progress (2026-09-03):** migration `20260903_0047` adds a durable
closed-code row. `POST /api/v1/rides/{ride_id}/messages` enforces exact
participant/role authorization, allowed active states, required idempotency,
per-user/per-ride rate limiting, a 100-message participant/ride cap, persistent
recipient notification, and minimized transactional outbox delivery. Detailed
ride reads expose only the latest signal while active and omit it after terminal
state. The worker suppresses terminal and stale delivery. Shared mobile UI shows
localized English/French/Arabic role-specific actions and reloads authoritative
state after sending. Fresh-PostGIS lifecycle, recipient, replay, wrong-role,
non-participant, terminal-state, notification, and stale-worker tests pass.

**Required closure:** approve the constrained signal set as the launch policy and
define retention/erasure and legal-hold treatment. Exercise provider outage and
fallback, delayed/duplicate/out-of-order delivery, weak-network recovery,
accessibility/localization, rate-limit comprehension, abuse reporting/escalation,
and support procedures. Verify that participants understand it is not an
emergency service and can safely resolve pickup failures. Do not add free text or
calling merely to close this gap; either needs its own approved privacy,
moderation, provider, cost, and operational design.

**Acceptance evidence:** approved policy and retention record; current-participant
authorization and privacy test pack; Android/iOS foreground/background/terminated
delivery matrix; EN/FR/AR/RTL, large-text and screen-reader acceptance; weak-
network, duplicate, stale, terminal-race and provider-outage traces; support and
abuse drill; closed-road cohort evidence measuring pickup-find success, time,
misunderstanding, fallback use and safety events; signed pilot thresholds and
stop/go decision. Until that bundle exists, this gap remains open despite source
implementation.

### GAP-024 — Implement operator-to-driver settlement and payout accounting

**Current gap:** driver earnings are created from completed payments, but there is
no operator settlement period, payable balance, payout instruction, cash offset,
adjustment/recovery policy, payout status, remittance statement or reconciliation
ledger. Refund policy currently assigns zero driver recovery/full operator funding.

**Risk:** recorded earnings do not explain what an operator owes a driver, what
was paid, or how cash collected by the driver offsets liabilities.

**Required closure:** approve cooperative accounting policy; model immutable
settlement periods and line items; distinguish earned, collected cash, operator
fee, refund funding, payable and paid; define approval, payout evidence,
corrections, disputes and export; never silently rewrite ride/payment snapshots.

**Acceptance evidence:** accountant-approved examples for cash and manual
transfer; ledger conservation tests; closed-period immutability; duplicate payout
protection; driver statement UX; controlled payout/reconciliation and audit.

### GAP-025 — Complete accessibility, localization, and usability acceptance

**Current gap:** localization catalogs, Arabic RTL support and many semantics are
implemented, but no complete WCAG/mobile accessibility report, screen-reader
journey, keyboard web journey, font scaling, contrast, touch-target,
reduced-motion, cognitive load or representative-user study is accepted.

**Risk:** disabled, older, low-literacy or Arabic-speaking users may be unable to
book, drive, review money, report safety issues or operate the console.

**Required closure:** define conformance target; audit passenger, driver,
applicant and operations critical journeys; test TalkBack/VoiceOver, keyboard,
focus order, dynamic type, 200% web zoom, contrast, non-color status, motion,
loading/errors and RTL clipping; conduct moderated tests with representative
passengers, licensed drivers and operations staff.

**Acceptance evidence:** issue-by-screen matrix with closure; automated checks
where useful; physical assistive-technology recordings; professional translation
review for French/Arabic; user-test findings and owner acceptance.

**Implementation progress (2026-09-09):** the guarded Android launcher can now
emit a non-overwriting, privacy-bounded device report after real registration and
login. It records supported SDK/ABI/model/locale/screen/package facts and two
backend-confirmed journey results without a raw serial, screenshot, credential or
submitted value. Source mutation tests keep the report partial and T4/deployment
acceptance false. No device was connected for this change, and accessibility,
RTL, lifecycle, crash, iOS/browser and representative-user evidence remain open.

The T4 laboratory catalog decomposes those open requirements into 56 closed
cases, eight each for supported matrix, Android, iOS, browser, accessibility/RTL,
degraded network/lifecycle and crash symbolication. Its validator cross-checks
actual source platform targets, prevents simulated physical/real-browser claims,
requires retained hashes and defect links, and credits evidence kinds
independently. The committed template remains 0/56 `NOT_STARTED`; this improves
execution discipline but closes none of the human/device acceptance gap by itself.

### GAP-026 — Accept routing narration and all operational copy

**Current gap:** localization infrastructure exists, but provider-generated
maneuver text, push payloads, safety/support explanations, payment recipient
instructions, legal text and unknown-server fallback content have not been
accepted end to end in all launch languages.

**Risk:** mistranslation or truncation can direct a driver incorrectly, misstate
money/status, hide safety limitations or expose raw backend text.

**Required closure:** inventory every backend and provider string; map closed
codes to reviewed client copy; keep unknown-code fallbacks safe and actionable;
professionally review domain terminology; test text expansion, RTL/bidirectional
identifiers, notification truncation, screen reader pronunciation and narration.

**Acceptance evidence:** versioned English/French/Arabic glossary; translation
approval; no raw internal error rendering; screenshot/notification/narration
matrix; unknown-event and mixed-direction tests.

### GAP-027 — Add a proportionate fraud and abuse control program

**Current gap:** rate limits, authorization, idempotency and audit reduce basic
abuse, but no approved controls cover account farming, location spoofing,
driver/passenger collusion, repeated cancellations, false transfer references,
refund abuse, document fraud, harassment or compromised staff behavior.

**Risk:** financial loss, unfair dispatch, unsafe users and operational overload.

**Required closure:** define abuse cases and privacy-bounded signals; start with
transparent rules and human review rather than opaque automated scoring; add
velocity/duplicate/reference/document anomalies, case linkage, appeal and
evidence retention; separate safety response from commercial fraud; measure
false positives and disparate impact.

**Acceptance evidence:** approved abuse model; adversarial tests; reviewer queue
and appeal procedure; aggregate false-positive/fairness review; audit and data-
minimization assessment; no automatic punitive action without documented authority.

### GAP-028 — Define notification reliability and fallback behavior by event

**Current gap:** an event-by-event source policy now classifies every current
transactional-outbox topic by allowlisted hint, live/push channel, urgency,
maximum delivery age, fallback, quiet-hour eligibility, and dead-letter owner.
Ride events reload current state and enforce source expiry; scheduled offers,
commitment, dispatch, fallback and unfulfilled outcomes now have transactional
push outbox paths; credential notices are informational. Live and FCM allowlists
derive from the same registry, FCM has policy TTL/priority, mobile accepts the
closed vocabulary, and unknown topics fail toward bounded dead-letter visibility.
Fixed-owner pending/dead-letter/lease/age gauges and an owner-preserving
Prometheus alert now make source failures attributable without exposing topics
or identifiers. Real provider SLOs, deployed alert routing, user
preference/quiet-hour execution, staff response, and physical-device fallback
acceptance remain absent.

**Risk:** stale ride offers arrive late, duplicate messages confuse users, or
important schedule/safety events disappear in generic retry behavior.

**Implementation progress (2026-09-05):** the registry and tests cover 13 outbox
topics. Event age is carried from the durable outbox claim, checked before any
business/provider access, and combined with current source-state validation.
Scheduled lifecycle writes now create persistent notification and outbox rows in
the same transaction. Five scheduled hint types have localized EN/FR/AR inbox
copy and use the shared one-hint authoritative restore path. The audit also found
and fixed a real coordination defect where the production live-event allowlist
rejected `RIDE_COORDINATION_MESSAGE` despite fake-publisher tests passing.
The production PostgreSQL fanout test now traverses every classified live hint.
Live and push channels are independently attempted with retry on partial failure;
worker cancellation is preserved. Scheduled offers also require an `OFFERING`
booking. Android TTL and iOS `apns-expiration` now derive from the original source
deadline, capped by offer/message expiry, and never restart on authentication or
retry. Expired/sub-second sends are suppressed. Transient device failures and
revocation failures no longer starve remaining registrations; cancellation still
propagates. Deterministic tests cover expiry boundaries, credential latency,
401 refresh, partial-device failure and deadline capping.

The local monitoring contract now emits stable owner buckets for dispatch,
scheduling and driver-compliance work plus fail-closed `unclassified` events.
The dead-letter alert retains that owner through PromQL, and validation rejects
dynamic topic/resource/user dimensions. Unit mutation tests and a real-PostGIS
authorization provider-failure/restart trace pass in the 956-test full report
at `backend/build/security-incident-full-tests.xml`. No real Alertmanager receiver,
staff roster, pager delivery or acknowledgement timing has been exercised.

Fresh-PostGIS scheduling evidence now asserts committed notification/outbox pairs
for offer, commitment and unfulfilled events; creation replay, duplicate acceptance
rejection and repeated worker runs do not add rows. Failures injected after SQL
flush prove rollback of business, notification and outbox changes for offer,
commitment, direct dispatch and unfulfilled branches. The no-supply fallback
leaves neither a phantom ride nor its intermediate notification/outbox rows.

The successful-handoff audit also exposed and fixed missing basic professional
eligibility checks. A shared scheduling helper now checks active account,
approved driver verification, selected/owned/active/verified vehicle and known
credential validity at offering, acceptance and handoff, in addition to city
authorization. The separate live-readiness guard is now implemented; `GAP-007`
still requires device/field acceptance and broader concurrency evidence.

Scheduling now locks and refreshes the booking before its offer/commitment/driver
rows; driver availability/location and vehicle mutation routes also refresh a
locked profile. Five real two-session PostgreSQL cases prove duplicate handoff,
both cancellation orders, offline-before-handoff and cancellation-before-accept
outcomes using an observed lock wait, deliberately stale ORM references and
fresh durable reads. Active-vehicle changes are offline-only. This narrows the
gap but does not prove all administrative revocation/configuration races or
independent HTTP/worker-process behavior; see `RACE-01` through `RACE-08` in
`testing.md`.

Successful direct-dispatch and successful fallback now have durable commit,
post-flush rollback, repeated-handoff and authoritative passenger-recipient proof.
The fallback cases cover a suspended account, expired vehicle verification and
expired known credential with another eligible driver receiving the live offer;
the ride remains unassigned until that candidate accepts. These extend the
five-event transactional evidence, not physical delivery acceptance.

**Required closure:** define and implement user preferences/quiet-hour scheduling
for eligible informational events; decide whether passenger cancellation needs a
persistent driver inbox row and how a cancelled pending offer wakes its candidate;
approve retry/dead-letter response targets, receiver routing and collapse
behavior; configure real FCM/APNs environments; measure per-event
delivery/visibility SLOs; and exercise
provider outage, delayed/duplicate/out-of-order hints, polling/inbox fallback and
staff escalation without personal payload data.
Measure device-visible source expiry under network/provider/OS delay; queue
headers alone cannot prove it. Define durable per-device retry progress: retries
can still duplicate delivery to previously successful channels/devices.
Finish multi-worker races, full offer/commitment recipient/privacy checks, fallback
candidate eligibility changes at acceptance, and physical live-readiness
acceptance before closing scheduling's deployment evidence.

**Commitment acceptance progress (2026-09-04):** `RACE-06` now has five
observed-wait PostgreSQL cases covering competing drivers, overlapping buffered
windows, allowed exact adjacency, cancellation releasing capacity after commit,
and the exclusion constraint rejecting a concurrent writer without service locks.
Four authenticated ASGI/PostGIS cases prove overlap handling, adjacent acceptance
and duplicate rejection, a genuine foreign-key fault, and atomic rollback after
notification/outbox SQL flush. The audit found and fixed misleading handling of
every integrity error as an overlap: only the exact driver-window exclusion now
becomes a `409`; other faults reach the sanitized internal-error boundary. Nine
classifier unit cases complete the 18-test focused pack. No scheduling policy or
schema changed. This does not close independent-process, physical-device,
immediate-work/protected-window, administrative-revocation, provider or field
acceptance; the `ACCEPT-01`–`ACCEPT-10` map in `testing.md` defines promotion.

**Acceptance evidence:** approved source/deployment matrix; transactional and
state-expiry tests; delayed/duplicate/out-of-order device traces; preference and
quiet-hour tests; polling/inbox fallback; dead-letter alerts, owner acknowledgement
and safe replay; multi-instance/provider-outage exercise; measured per-event SLO
and signed operations/product acceptance. The gap remains open until those real
environment results exist.

### GAP-029 — Retire or tightly govern transitional `/admin` authority

**Current gap:** national operations uses scoped grants and an operations
audience, while older global `/admin` compatibility routes remain for several
flows in local/test applications. The source and deployment boundary removes all
21 legacy operations from staging/production routing and OpenAPI. Scoped vehicle
verification and cross-market-safe account-security commands exist. An executable
source gate now proves maintained mobile and web sources have zero legacy callers,
and privacy-bounded served/blocked telemetry exposes any attempted use. Final code
removal, a dated retirement decision and production rehearsal evidence are still
absent.

**Risk:** an unrestricted legacy administrator path bypasses the intended city/
operator scope model and becomes a high-value attack or mistake surface.

**Required closure:** inventory every `/admin` route and caller; migrate supported
operations to scoped APIs; disable legacy routes in non-legacy deployments or
restrict them to documented break-glass use; add telemetry and expiry; ensure
bootstrap authority cannot become routine national access.

**Acceptance evidence:** route/caller inventory; zero normal production clients;
configuration-enforced disablement; scope regression tests; break-glass drill and
audit; dated removal decision for each retained route.

**Implementation progress (2026-09-01):** `Settings` now defaults
`TAXIMOBILE_LEGACY_ADMIN_API_ENABLED` on only for development/test, defaults it
off for staging/production, and refuses to start either production-like
environment if true. The v1 router factory conditionally mounts all four legacy
router families together; a route-level regression proves the disabled OpenAPI
contains zero `/api/v1/admin*` paths while representative scoped operations
remain. Production Compose, paid staging, and free synthetic-testing manifests
pin the value to false, and the production manifest validator rejects changes.
The 21-route inventory and successor mapping are in `api.md`. Payment, support,
safety, audit, pricing, driver-application approval, and vehicle verification
have scoped successors. Vehicle verification is tied to selected application
evidence, city permission, a reviewable application, optimistic version, recent
MFA, idempotency, and fixed-field audit data; its migrated-PostGIS workflow is
covered by the backend suite. Session revocation, suspension, and reactivation
now use operations-authenticated, recent-MFA, idempotent commands with controlled
reason/case references and fixed-field audit. Only `PLATFORM_ADMIN` has the
permission; the target must be associated with the route market, and the actor
must cover every market in the target's passenger, driver, booking, case, safety,
or staff history. Tests cover revoke/replay/conflicting reuse, suspension/login
denial, reactivation, unrelated-target hiding, and partial cross-market denial.
All mobile and operations sessions plus push registrations are revoked. The web
console exposes the module only with that permission, has no broad user search,
requires exact case-derived UUID, selected market, controlled reason/reference
and typed action confirmation, clears confirmation on submission, and never
replays after MFA step-up. JS and Wasm tests cover destination permission, input
guards and response decoding. The gap remains open until the zero-client
inventory, least-privilege access review, containment/recovery and break-glass
drills, telemetry, and dated
legacy removal decision are evidenced. The switch must not bypass those controls.

**Retirement-control progress (2026-09-07):**
`validate_legacy_admin_retirement.py` scans only maintained client source roots,
rejects `/admin` endpoint literals without echoing source content, and is wired
into both documentation/provenance and backend CI jobs. Its current scan reports
zero mobile/web callers. Request telemetry records only fixed `served` or
`blocked` outcomes for the exact configured legacy namespace; blocked probes do
not expose their raw path. Routed local/test responses carry `Deprecation: true`
and a non-secret warning. The 26-rule Prometheus set stops promotion if a legacy
route is served, and the immutable 26-panel operations dashboard separates routed
compatibility use from disabled-route probes. This is source enforcement, not a
production traffic audit or an owner-approved removal date.

### GAP-030 — Verify retention, legal holds, and erasure across every store

**Current gap:** case and driver-document retention workers exist, but no complete
retention matrix covers accounts, sessions, locations, rides, offers, payments,
notifications, analytics, audit logs, logs/metrics, object storage, device caches,
backups and exports. Backup expiry and legal-hold reconciliation are unaccepted.

**Risk:** data is deleted too early for legal/accounting duties or retained far
longer than necessary, especially in observability and backups.

**Required closure:** map every data store and copy; define event-based retention,
legal basis and hold behavior; make jobs observable/idempotent; minimize or
pseudonymize analytics; expire exports and device/browser caches; document backup
cryptographic/physical expiry; periodically sample outcomes.

**Acceptance evidence:** approved matrix tied to schema/config; time-shifted
retention tests; hold/release tests; object/log/cache/backup deletion evidence;
aggregate counts and immutable erasure facts without retained erased content.

### GAP-031 — Add complete security-incident operations

**Current gap:** migration `20260907_0050` and a restricted operations API now
provide market/city-scoped security-incident creation, filtered list/detail,
append-only timeline entries, linked immutable audit IDs/external runbook
references, and a forward-only `OPEN` → `CONTAINING` → `CONTAINED` →
`RECOVERING` → `RECOVERED` → `CLOSED` lifecycle. Writes require recent MFA,
idempotency and `manage_security_incidents`; stale transitions are refused by
optimistic version. The database rejects timeline update/delete, and audit rows
record controlled codes/flags rather than copying incident narrative.

Migration `20260907_0051` now adds one-time postmortem completion with completion
time/actor, fixed outcome, current optimistic version and referenced immutable
timeline evidence. `FOLLOW_UP_REQUIRED` must link an approved external work
reference. Database checks reject partial, pre-closure or non-closed completion,
and partial deadline indexes prepare bounded overdue monitoring.

The protected operations web workspace now exposes this module only with the
dedicated permission. It loads the bounded market queue, supports market/city
creation, detail/timeline review, referenced immutable facts and only the exact
next lifecycle action. Inputs are bounded and typed-confirmed; confirmations are
cleared before submission, stale conflicts reload authority, and MFA never
replays the failed command. The closed-incident view adds the one-time completion
control and shows immutable completion authority/outcome.

Migration `20260908_0052` now adds four closed responsibility types:
`SECURITY_RESPONSE_LEAD`, `COMMUNICATIONS_LEAD`, `OPERATIONS_LIAISON` and
`POSTMORTEM_OWNER`. Opening an incident assigns its reporter as response lead.
One active tenure is allowed per incident/responsibility; reassignment releases
the prior tenure once and preserves it as append-visible history. Deletion or
later mutation is rejected by the database. Assignment requires recent MFA,
idempotency, current incident version, an exact active user with a live
platform-administrator grant in the incident market, and a controlled approved
roster/shift reference. Ineligible candidate variants receive one generic
conflict and no search endpoint exists. Reassigning response lead updates the
incident lead and every assignment adds a generated timeline fact.

The web workspace shows active/released tenures and supports typed-confirmed
assignment. Seven security-incident model tests now pass in both JS and Wasm,
bringing each browser target to 57 tests; the source-contract gate covers all
nine incident client operations within 112 expanded web HTTP calls and proves
the responsibility path selector fails closed to the four values.

Both protected application-role scrapes now execute one five-second-bounded
aggregate query and expose only availability plus fixed SEV1-SEV4 counts for open
incidents, missed containment deadlines, pending postmortems and missed
postmortem deadlines. Database/timeout/malformed-result failures emit unavailable
and omit counts. Five reviewed Prometheus rules cover snapshot loss, open
SEV1/SEV2 incidents, critical and lower-severity containment breaches, and
overdue postmortems; three immutable dashboard panels expose the same bounded
state. API and worker duplicate snapshots are reduced with `min`/`max`, not
summed. No incident, market, city, actor, narrative or evidence identifier enters
a metric or alert label.

This remains partial source closure. There is no authoritative roster or shift
service feeding these assignments, accepted webhook/pager delivery or escalation SLO, containment-command
orchestration, provider/key rotation adapter, structured regulatory/user
notification approval, accessibility acceptance, concurrent multi-operator
handoff rehearsal, or exercised production drill. Database grant eligibility
does not prove that the person is on duty or has accepted the responsibility.

**Risk:** security events are handled through generic notes or direct database
actions, losing urgency, evidence and accountability.

**Required closure:** define incident severities and roles; add or integrate a
restricted incident workflow; link immutable audit facts without copying excess
personal data; support containment (session/grant/key/provider revocation),
regulatory/user notification decisions, timeline, recovery and postmortem; retain
break-glass audit.

**Implementation progress (2026-09-08):** the dedicated 16-unit/static and two-
PostGIS branches prove create/replay, scoped retrieval, evidence linking, all five ordered
transitions, stale-version refusal, one-time postmortem completion/replay,
ten-event sequence, initial and replacement responsibility assignment, generic
ineligible refusal, exact-market grant check, concurrent one-winner
version/idempotency authority,
content-minimized audit metadata and SQLSTATE `55000` on timeline or assignment
history mutation, fixed zero-filled severity buckets, deadline transitions,
privacy-safe failure behavior and alert mutation refusal. Migration 0052 upgrade
and `0052 → 0051 → 0052` round trip passed, followed by all 992 backend tests on
fresh PostGIS.
This is local dirty-workspace evidence, not a staffed tabletop, web accessibility,
external containment, communications decision, or production timing result.

**Acceptance evidence:** approved on-call roster and shift source; concurrent
assignment/hand-off test; keyboard/screen-reader workspace acceptance; tabletop
plus technical drill for compromised passenger, driver and staff accounts and a
leaked provider credential; real receiver acknowledgement/escalation timings;
complete responsibility/timeline/audit reconciliation; communications decision;
provider/session/grant containment references; postmortem and follow-up ownership.

### GAP-032 — Approve SLOs, pilot thresholds, and expansion decisions

**Current gap:** analytics definitions and readiness stages exist, but target
values for availability, dispatch, offer fairness, cancellation, scheduled
fulfillment, support/safety response, payment backlog, driver onboarding, crash
rate, retention and expansion are not approved from real operations.

**Risk:** a city can be declared successful or expanded using arbitrary or
post-hoc criteria.

**Required closure:** establish baseline and target ranges before pilot; define
minimum sample/privacy suppression, observation period, owner, data quality and
what triggers pause, remediation, activation or expansion; include driver and
passenger qualitative feedback and cooperative review.

**Acceptance evidence:** signed metric dictionary/thresholds linked to dashboard
definitions; synthetic validation; pilot review agenda; immutable readiness
decision citing measured period; no suppressed cell treated as zero.

## 7. P2 — hardening required before national scale

### GAP-033 — Strengthen continuous integration and quality gates

Add web JS/Wasm builds and browser tests, all-ecosystem vulnerability scanning,
coverage/changed-code expectations, documentation-link checks, OpenAPI/client
drift checks, migration graph checks, deterministic asset validation, container
scan and signed artifact provenance. Keep jobs pinned and ensure release builds
cannot use the current “allow unsigned/missing Firebase for verification” flags.

**Closure evidence:** clean-commit CI exercises every shipped target and blocks
contract, migration, security, artifact or documentation drift.

**Implementation progress (2026-09-01):** a documentation/provenance job now
checks local links, standing blocks, all 37 gap headings, T0–T10 testing phases,
the reported migration head and whitespace, then generates source-candidate
evidence. A dedicated web job runs JS/Wasm browser tests, builds the compatibility
distribution and applies release packaging/bundle checks. Existing Python audit,
credential, OpenAPI/mobile contract, Compose, Prometheus, Android and iOS gates
remain. CI now also pins and locally validates dependency review, trusted-push
Gradle graph submission, backend image SPDX SBOM/provenance, and a blocking
high/critical OS/library image scan. The complete push and pull-request workflows
passed at immutable `de69829a`; full browser E2E, existing-alert remediation,
complete Gradle/JavaScript vulnerability coverage, mobile/web SBOMs, coverage
policy and signed provenance remain open.

**Implementation progress (2026-09-08):** CI now generates one deterministic,
secret-free source-contract inventory after installing the backend. It enumerates
all 244 FastAPI HTTP operations and the WebSocket path, validates and emits all 52
Alembic revisions with one root/head, and emits all 22 server-owned permissions
across nine role templates. The inventory is retained in the run summary and its
hash is bound into the same candidate evidence record as the backend SPDX SBOM.
Mutation tests reject removal of generation/provenance binding. The clean
immutable `de69829a` GitHub runs now verify this path; independent review and
signed promotion evidence remain open.

The documentation/provenance job now also validates the executable T0–T10 phase
catalog and its all-`NOT_STARTED` template. Mutation coverage rejects removal of
that gate. CI validates the promotion contract but cannot create an accepted
device, hosted, staff, city or real-user phase record.

**Implementation progress (2026-09-09):** six dependency-free runtime scenarios
now execute the static web compatibility boot and exact-origin/path header
scoping. The packaged web file manifest and limitation-marked Android/iOS role
manifests are each hash-bound to clean source evidence and retained in the CI run
summary; mutation tests reject removal of any binding. The local web package has
81 files and 33,777,513 bytes excluding three maps. The Android 1.0.0
verification APKs and their hashes are locally recorded; iOS execution remains a
macOS CI gate. This is stronger candidate provenance, not signing, SBOM coverage,
remote-CI success, device acceptance or a public release.

The backend CI job now also executes the bounded 20-scenario/66-test T2 persona
catalog and retains its JSON plus JUnit evidence under the same clean-candidate
binding. CI wiring mutation tests reject removing the runner, either artifact,
or the explicit non-acceptance warning. This makes simulated journey drift
visible without treating a source-level unit harness as database, provider,
device, security-review, or field evidence.

The backend job now retains a full-suite JUnit report, collects safe PostGIS/
migration/clone/authority metadata, runs a guarded logical backup/restore, and
generates a T3 report that requires named migration-lock, concurrency, worker
termination/reclaim and reconciliation tests. All four artifacts are bound to candidate provenance, and CI mutation
tests reject removal of execution, binding, retention or the explicit
non-acceptance warning. The local 992-test plus restore record passes all six T3
evidence kinds; a clean remote run and formal engineering acceptance remain open.

### GAP-034 — Reduce contract and implementation drift

Several documents and operations UI/source files are large and route inventories
are hand-maintained. Generate API inventory from OpenAPI, generate migration and
permission matrices, split oversized UI/operations modules by bounded domain, and
add a dated status check so “target,” “implemented,” and “accepted” cannot drift.
Do not split the backend into distributed services merely to reduce file size.

**Implementation progress (2026-09-08):** executable source gates now extract
all handwritten mobile operations and 111 expanded operations-web HTTP calls from
their real Ktor call sites and compare method/path pairs with FastAPI OpenAPI.
The web extractor fails on unknown call shapes, arbitrary route variables,
unreviewed dynamic segments, permissive action selectors, and calls outside the
single versioned endpoint builder. Centralizing that builder also removed a real
double-`/api/v1` defect in the control-plane and payment gateways. CI and the
portable backend gate run both validators, with parser failure tests and a
current-workspace compatibility test. The deterministic source-contract inventory
now generates the complete OpenAPI operation list, Alembic graph and server role-
permission matrix; it fails on duplicate operation IDs, ambiguous/dangling/cyclic
migrations, missing role mappings or unknown permissions. Payload-schema/client
model generation, further oversized-module splits, and authenticated external
acceptance evidence remain open; this gap is therefore reduced, not closed.

The phase-evidence index is now the dated accepted-status report boundary: exact
candidate, catalog revision, phase state, evidence kinds, controlled references,
digests, sign-off functions, defects and invalidation can be checked without
copying sensitive payloads into Git. The repository template intentionally makes
no acceptance claim. External reference authenticity and further oversized-module
splits remain open.

**Closure evidence:** smaller owned modules, generated contract reports, link and
status lints, and no duplicate policy authority.

### GAP-035 — Prove multi-city and multi-operator isolation under scale

Exercise grants, SQL filters, analytics suppression, payment recipients,
configuration replacement, document review, fixed routes, scheduling and case
queues with many cities/operators and multiple replicas. Review query plans and
partition/index strategy only from measured need. Test one city pause without
affecting another and prevent cross-city cache or live-event leakage.

**Closure evidence:** adversarial multi-tenant integration/load report, no scope
leak, acceptable plans/latency, and independent city lifecycle proof.

### GAP-036 — Establish release, support, and lifecycle management

Define semantic application/API/config versions, supported mobile/web versions,
forced/minimum upgrade policy, deprecation windows, release channels, rollback/
forward-fix ownership, maintenance windows, status communication, public support
contacts, app-store response ownership and end-of-life handling.

**Implementation progress (2026-09-08):** the source now has a closed six-surface
client identity (`ANDROID`/`IOS` passenger and driver, applicant web, operations
web), strict three/four-component numeric release versions, positive bounded
builds, and a complete minimum/recommended policy with a controlled revision.
Production-like configuration cannot disable enforcement or omit a surface.
Ordinary v1 HTTP requests reject missing/malformed identity and obsolete versions
with safe `426` errors; the live-event socket closes unsupported clients with
`4406`. A command-free preflight reports `SUPPORTED`, `UPDATE_AVAILABLE`, or
`UPGRADE_REQUIRED`. Android/iOS restore uses a localized fail-closed gate, both
web surfaces block behind reload/retry guidance, release packaging validates web
metadata, and manifest/API/mobile tests cover parser, policy, CORS and rejection
branches. Current source contracts are 244 backend HTTP operations, 83 mobile
HTTP plus one WebSocket operation, and 112 web HTTP operations.

This is not closure. The default `1.0.0`/`baseline-1` values are development
baselines, not an approved public support policy. Still required are named
release/support owners, supported OS/browser/store channels, deprecation and
emergency timelines, public status/support contacts, immutable signed current and
obsolete artifacts, staged policy-raise/rollback/forward-fix evidence, store/web
propagation and cache testing, communication templates, account/data continuity,
and end-of-life approval. Mid-session command handling must also be field-tested:
the backend remains authoritative even if a client does not present the friendly
upgrade screen until refresh/restart.

**Closure evidence:** versioned release policy exercised across a compatible and
an intentionally obsolete client, with communication and rollback records.

### GAP-037 — Govern data quality and analytics evolution

Define event completeness checks, late/duplicate handling, definition versioning,
source reconciliation, small-cell suppression review, dashboard ownership and a
process for changing metrics without rewriting historical meaning. Do not add
individual tracking, demand forecasting or automated fairness decisions without
measured need and a new privacy/product review.

**Closure evidence:** reconciled production-like event totals, data-quality
alerts, versioned definitions, privacy review and an audited change example.

## 8. Explicit deferrals — not current launch blockers

These capabilities must remain hidden and unadvertised. They become gaps only if
the approved launch scope changes to require them.

| Deferred capability | Current rule |
| --- | --- |
| CMI/card processing | Keep `CARD` reserved but unavailable. Cash and controlled manual transfer are the launch methods. |
| Firebase databases/functions/storage/hosting/phone auth/Analytics | Do not add them merely because FCM and Crashlytics are used. Preserve provider-independent backend/database/storage boundaries. |
| Recurring scheduled bookings | Single bookings only. |
| Fixed-route segment fares, seat pooling and intercity operation | Do not expose until regulatory, operational and product contracts exist. |
| Dynamic/surge pricing | Not part of the cooperative transparent tariff model. |
| Passenger view of online taxis | Prohibited. Supply remains private until backend assignment. |
| Passenger selection of a specific driver | Prohibited. Drivers choose through backend offers. |
| General-purpose image upload | Prohibited; only approved protected driver-document formats use the protected workflow. |
| Advanced fraud scoring, demand forecasting and individual analytics | Require measured need, fairness/privacy review and explicit authority. |
| Automated cooperative governance/voting | Future product decision; current software must not imply it exists. |
| Multi-operator revenue sharing and automated payouts | Requires the GAP-024 accounting foundation and separate approved policy. |

## 9. Recommended closure sequence

### Stage 0 — Freeze evidence

Close GAP-001. Choose the exact candidate commit and make CI results reproducible.
No later acceptance should refer to a moving working tree.

### Stage 1 — Approve scope and foundations

Close GAP-004, GAP-017 and the policy portion of GAP-007. In parallel provision
GAP-002 and GAP-003, establish GAP-005, and begin GAP-016. This determines what
may lawfully and operationally be tested.

### Stage 2 — Integrate launch providers and duty operations

Close GAP-006, GAP-008, GAP-009, GAP-010, GAP-011, GAP-012 and GAP-015 in
production-like staging. Complete signed mobile and secure web delivery under
GAP-013 and GAP-014.

### Stage 3 — Stress and independently review

Close GAP-016 and GAP-018. Resolve any P1 item touched by the pilot scope,
especially account recovery, accessibility, communications, retention and
legacy-admin authority.

### Stage 4 — Controlled acceptance and bounded pilot

Close GAP-019, approve the launch thresholds in GAP-032, and issue a formal
go/no-go decision. Start with one city and a bounded cohort. Preserve emergency
pause and rollback. Do not activate a second city until the first has a measured
post-launch review and all new city evidence is independently supplied.

## 10. Go-live evidence checklist

Every item below must be checked by the named accountable owner. A link to a
source file alone is not sufficient evidence.

- [ ] Candidate release is a reviewed immutable commit and every artifact maps to it.
- [ ] Backend, migrations, Android, iOS, JavaScript, Wasm, browser E2E, dependency and container gates pass for that commit.
- [ ] One city/operator/service scope has current legal, commercial, tariff, privacy and safety approval.
- [ ] Production host, TLS, DNS, IAM, secrets, network boundaries and digest-pinned images are accepted.
- [ ] Managed PostGIS migration, backup, PITR/restore, failover, retention and capacity evidence is accepted.
- [ ] Operations staff have least-privilege grants, MFA, recovery, access review and separation of duties.
- [ ] Map style/tiles and selected routing graph are licensed, versioned, monitored and field-tested.
- [ ] Driver-location and geocoding policies are approved and meet measured field requirements.
- [ ] FCM/APNs delivery, token lifecycle, dead letters and localized messages pass on real devices.
- [ ] Real payment recipient, cash controls, transfer reconciliation and refund procedures are exercised.
- [ ] Support/safety staffing, pager, escalation, emergency limitations, legal holds and shift handoff are exercised.
- [ ] Protected document storage, keying, scanning, retrieval, restore and erasure pass production-like tests.
- [ ] Signed passenger and driver releases pass physical-device, upgrade, weak-network, accessibility and RTL tests.
- [ ] Applicant and operations web pass secure-hosting, browser, CSP, CSRF/cookie, accessibility and sensitive-flow tests.
- [ ] Monitoring, logs, dashboards, alerts, Crashlytics, SLOs, on-call and incident runbooks are live and drilled.
- [ ] Threat model, penetration retest, SBOMs, vulnerability scans and privacy/legal review are approved.
- [ ] Representative load, multi-replica soak, provider degradation and rollback meet agreed SLO/RPO/RTO.
- [ ] Full controlled city journey reconciles rides, offers, payments, earnings, cases, notifications, analytics and audit.
- [ ] Pilot success/pause/stop criteria and accountable decision makers are recorded before launch.
- [ ] Residual risks, known limitations, expiry dates and follow-up owners are explicitly accepted.

## 11. Rules for closing a gap

1. Assign one accountable owner and a due/review date.
2. Link the approved product/policy decision when closure required judgment.
3. Link immutable implementation and environment/configuration versions.
4. Attach automated results and human/provider/field evidence required above.
5. Record negative and failure-path evidence, not only a happy-path screenshot.
6. Have a second qualified reviewer approve P0 closure.
7. Update the owning domain document and this register in the same reviewed
   change. Never delete gap history; mark it closed with date and evidence.
8. Reopen a gap when its provider, city, policy, artifact, threat model or
   acceptance evidence materially changes or expires.

Recommended closure record:

```text
Gap: GAP-NNN
Status: OPEN | IN PROGRESS | BLOCKED | ACCEPTED | REOPENED
Owner:
Target environment/city/version:
Decision links:
Implementation commit and artifact digests:
Automated evidence:
Human/provider/field evidence:
Negative/failure evidence:
Residual risks and expiry:
Independent reviewer and date:
```

Until every applicable P0 item has an accepted closure record, TaxiMobile remains
a development system and must not carry a public passenger, production driver
identity document, real operational location stream, or live customer payment.
