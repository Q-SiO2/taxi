# TaxiMobile documentation

> **Next source packet — 25 October 2026:** migration `20261025_0054` and the
> [durable S3 workflow](launch/document-s3.md) now reserve hidden upload metadata,
> enforce a final owner/version/lease transaction and reconcile interrupted/late
> writes. API/worker configuration and shutdown ownership are wired in source;
> local reports contain 1,142 unit, 62 API and 17 PostGIS recovery/lifecycle
> passes, plus three subsequent SQL lock/lease regressions. Their source scopes
> are qualified in the packet. Native full-suite CI, hosted storage/feeds/key
> recovery and rollout remain open.
>
> **Accepted source predecessor — 24 October 2026:** the
> [protected document correction](launch/document-storage.md) passes all eight
> required CI jobs and 1,342 backend tests, plus a real local ClamAV/custom-fixture
> rehearsal. The owner-selected [private S3 successor](launch/document-s3.md)
> transport checkpoint passed 1,115 local unit tests before the durable successor.
> Hosted storage, feeds and key/retention acceptance remain open.

> **Current packet — 24 October 2026:** all eight required CI jobs pass for source
> [2919835](launch/database-tls-ci-terminal-20261024.json). The [staging upgrade packet](launch/staging-upgrade.md) records an encrypted
> database backup, matching 81 public-table counts after isolated restore and a
> successful local 0053 migration/readiness check, with explicit platform and
> failure qualifications. [Verified database transport](launch/database-tls.md)
> now passes 1,317 full backend CI tests, including eight real TLS checks, with
> no failures/errors/skips. Android/web, unsigned iOS and dependency review pass.
> Hosted schema remains 0052 and TLS is disabled;
> protected document ingestion and matched rollout remain open.

> **Current source packet — 23 October 2026:** the
> [session/release correction](launch/session-recovery.md) addresses idle logout
> and the actual member-register CI packaging failure. Local protocol, production
> packaging and bounded Chrome boot now pass. The [dependency correction](launch/dependency-refresh.md)
> addresses the next actual CI audit failure; its eight required CI jobs pass,
> while hosted acceptance remains open.

> **Source migration - 23 October 2026:** `20261023_0053` adds the explicit
> operator membership policy for the Fès union launch. It is a source change;
> [isolated migration/authority verification](launch/union-membership.md) is
> recorded. The [staff-register extension](launch/member-register.md) adds scoped
> audited operations UX and localized driver guidance; its runtime verification,
> immutable CI and deliberate deployment remain separate acceptance steps.
> The alpha's deployed schema/evidence retain their original identity.

> **Active goal - 23 October 2026:** establish real-world deployment with full
> documented functionality. Start with [the detailed execution plan](real-world-launch.md)
> and [roadmap](roadmap.md): R0 reconciliation, production capability closure,
> real device/provider/staff acceptance, authorized city pilot and public release.
> Android, iOS and both web portals are included. Spending, operator/legal and
> activation decisions retain their explicit gates. The alpha below is the
> regression baseline, not real-world acceptance.

> **Active delivery - 23 October 2026:** native v23 / live web v10 now pass the
> scoped synthetic board path twice, at **16:22 / 11:07**, with disclosed
> observer/setup qualifications. Both cash rides have eight successful business
> requests exactly once; final driver state is offline and pending cash zero.
> Folded Streets, Street Press, Glazed Machine and Notepad are implemented choices;
> there is no separate color menu or taxi/city hero. The deployed web passes
> 103 HTTP checks and selected actual four-style/EN/FR/AR timeline review.
>
> Start with [the current checkpoint](board-alpha.md), [the handoff](board-alpha-handoff.md)
> and [presenter script](board-demo.md). [roadmap.md](roadmap.md) remains the plan
> for **board alpha -> authorized pilot -> public release**. Railway recovery is
> applied within Trial limits, with both volumes preserved. Owner visual review,
> physical Android, iOS, broader accessibility/state coverage, field transport,
> real money and later launch gates remain separate. The 213-view inventory is
> not runtime acceptance of every view. Historical records keep their own identity.

## Six core entry points

| Read to | Start here | Detailed authority when needed |
| --- | --- | --- |
| Understand the project and status | This README | Dated [readiness.md](readiness.md); source inventory below. |
| Implement product journeys | [product.md](product.md) | [design.md](design.md), [ui.md](ui.md), [extended_ui.md](extended_ui.md) and relevant domain. |
| Understand system boundaries | [architecture.md](architecture.md) | [implementation.md](implementation.md), [api.md](api.md), [database.md](database.md), [security.md](security.md). |
| Set up, build, test and hand off | [workflow.md](workflow.md) | Linked backend/client/infra setup guides, [testing.md](testing.md) and evidence catalogs. |
| Deploy and verify staging | [deployment.md](deployment.md) | Railway preflight, resource/cost/secret controls, actual integration and safe shutdown. |
| Choose and execute the next task | [roadmap.md](roadmap.md) | [union_demo.md](union_demo.md) scenarios; [gaps.md](gaps.md) real-world acceptance. |

These entry points consolidate delivery navigation without deleting specialized
API, legal/privacy, security, data or business contracts referenced by code and
project instructions. The old numbered delivery plan is [historical](history/roadmap_before_alpha_20261012.md).
Read relevant sections rather than every document; no separate audit or historical
percentage overrides the active A/B/C sequence. Future consolidation must preserve
contracts and update all links/instructions/validators before removing an authority.

This directory is the product, architecture, security, and delivery authority for
TaxiMobile. It describes both the intended system and the software currently in
the repository. Those are not the same kind of statement.

## Current project standing

**Current delivery priority:** the essential alpha journeys and ten exit gates in
[roadmap.md](roadmap.md). [union_demo.md](union_demo.md) retains the wider 20-journey
board, including optional advanced demonstrations, and the rehearsal procedure.
Report both separately; neither automated tests nor fixture screens accept a
physical passenger/driver/browser journey or authorize live transport.

**Historical source assessment:** 2026-09-09, refreshed 2026-10-02.
Current alpha evidence and candidate identities are in [board-alpha.md](board-alpha.md).

**Migration head:** `20260908_0052`

**Engineering assessment:** approximately **84% of the weighted source scope**
is implemented; this is not a launch-readiness percentage. The complete scoring
matrix, fresh checks, source evidence and limitations are in
[`readiness.md`](readiness.md). Use [`workflow.md`](workflow.md) for the practical
requirement-to-verification-to-release workflow. All 19 P0 deployment gates
remain unaccepted in the gap register.

**Overall standing:** broad provider-independent implementation exists and passes
local automated verification, but TaxiMobile is **not ready for public or live
pilot deployment**. The unresolved work is tracked in [`gaps.md`](gaps.md).
The latest local full isolated-PostGIS regression through migration 0052 passed
1,090 backend tests with zero failures, errors or skips. Server commit
`2d6a68b04eccd793d5d071b8f26bba67568bf63b` passes
[push CI](https://github.com/Q-SiO2/taxi/actions/runs/37000510927) and
[PR CI](https://github.com/Q-SiO2/taxi/actions/runs/37000515435), but GAP-001 remains open because
independent review, signing, registry digest, and release approval are
absent. Owner-authorized main protection is now configured and verified. Main-only
GHCR publication is implemented but has not run; image storage does not provide
live hosting. The subsequent Android protected-session source patch has local host
evidence and complete passing push/PR CI for `cc19776`; physical-device acceptance
remains open. OpenAPI tooling now has passing push/PR CI on `17a94df`, with both
retained packets' hashes and source identities reconciled; subsequent registry
protocol and packaged-identity patches now pass immutable push/PR CI through
`7c7982a`, but a successful reviewed main publication remains absent;
see `implementation.md` and the ordered native-storage testing pack.
Android artifact tooling also checks actual packaged APK identity rather than
metadata alone, with fail-closed file confinement and non-distributable reports;
signing/device evidence remains absent. A further compiler compatibility repair
pins actually loaded R8 9.1.56 for Kotlin 2.4 and cross-checks APK markers,
mapping IDs and fresh minification logs. It has local build/script evidence but
requires its own immutable CI and minified-device journeys before acceptance.
Optional signed-package inspection now compares both role APKs against explicit
public signer fingerprints with the SDK verifier and rejects debuggable packages.
Signature matching is not owner approval; no production identity, signing key,
signed minified release or distribution acceptance was supplied by this tooling.
Historical `168c350` results in the summary table below describe that earlier candidate only.
The local regression includes the focused
security-incident unit/PostGIS slice, aggregate deadline-alert coverage and
migration upgrade/downgrade coverage, including explicit incident responsibility
assignment and append-visible reassignment history. Machine-readable T3 evidence
also verifies the current migration/PostGIS metadata, named concurrency and
worker-recovery cases, zero residual test clones and revoked temporary local
database authority. A guarded current-head logical restore also reconciled all
81 public table counts and schema-object totals, then removed its temporary
database and dump. All six T3 evidence kinds are now locally present, but T3 is
not accepted without engineering sign-off and an ordered phase record.

The terms below have one meaning throughout these documents:

| Term | Meaning |
| --- | --- |
| **Specified** | The behavior is an approved requirement. It may not exist in code. |
| **Implemented in source** | A concrete code path, schema, and applicable tests exist in this repository. |
| **Locally verified** | The relevant automated checks passed in the workspace on the audit date. |
| **CI-wired** | A CI job is defined in the working tree to verify the path on push/PR. Commitment and a passing immutable remote run must be established separately. |
| **Deployment-accepted** | A named owner has supplied real environment, provider, legal, security, operational, and device evidence. |
| **Deferred** | The feature is intentionally outside the current launch scope. |

“Delivered,” “complete,” or “implemented” without another qualifier means
**implemented in source**, never deployment-accepted. A route, screen, migration,
Compose manifest, or passing local test cannot establish legal approval, provider
availability, production security, operational staffing, or real-world service
quality.

## Status summary

| Area | Repository standing | Deployment standing |
| --- | --- | --- |
| Passenger and driver mobile | Shared Android/iOS source, role-specific release identity and compatibility preflight, maps, rides, payments, support/safety, fixed routes, scheduling, recruitment, offline-code recovery, active-session controls, and password change are implemented. The immutable `168c350` push and pull-request runs produced limitation-marked Android/iOS manifests and linked both iOS Release simulator apps. | MapLibre issue 824 still prevents native iOS test linking. Approved support/deprecation policy, intentionally obsolete signed-build testing, verified contact ownership, physical Android/iOS matrix, signed store artifacts, production Firebase/APNs, accessibility, network-loss, navigation, and crash-symbolication acceptance are open. |
| Public applicant and operations web | JavaScript and Kotlin/Wasm sources, release identity/preflight gate, protected operations authentication, staff maker-checker queue, city control plane, recruitment, pricing, payment, fixed-route, scheduling, case, security-incident, audit, and analytics modules are implemented. Immutable `168c350` CI passed static preflight, both browser targets, compatibility packaging without maps, and clean-source manifest binding. | Old/current hosted-release switching, full browser E2E, production CSP/hosting, accessibility/RTL, authoritative staff/incident rosters, protected-document browser acceptance, and production operations-account enrollment remain open. |
| Backend and database | FastAPI modular monolith, six-surface release compatibility enforcement, eight worker loops, PostGIS schema through migration `20260908_0052`, scoped operations APIs including transactional staff dual control and security-incident responsibility/postmortem coordination, mobile recovery/session-control APIs, and local unit/API/integration coverage are implemented. | Approved release policy/drill, managed PostGIS, production migration rehearsal, encrypted backup/PITR, staging restore, capacity/soak, high availability, authoritative duty rosters, staffed incident drills, and production incident evidence are open. |
| Maps, places, routing, push, and crash reporting | MapLibre composition, normalized place search/reverse lookup with a fail-closed Nominatim-compatible adapter, Valhalla/GraphHopper adapters, FCM/APNs wiring, Crashlytics release boundaries, and a fail-closed GAP-006 evidence contract exist. | The committed GAP-006 record is `NOT_STARTED`; no production style/tile or geocoding source, accepted data/license and multilingual place benchmark, promoted routing graph, required-language physical-device matrix, Firebase credentials, or controlled delivery/crash proof is recorded. |
| Payments | Cash, manually reconciled bank/M-Wallet transfer claims, versioned recipients/capabilities, refunds, and immutable financial snapshots exist. | Real recipient verification, controlled transfers/refunds, reconciliation staffing, statement fidelity, cash controls, and payout/settlement operations remain open. CMI/card is deferred. |
| National rollout | City/operator/configuration models, scoped grants, MFA, readiness gates, analytics, emergency pause, repeatable rollout workflows, backend-enforced maker/reviewer separation and fail-closed GAP-004 pilot/GAP-005 staff-governance evidence contracts exist. | Both committed records are deliberately `NOT_STARTED`; no city has supplied legal/operator approval, real readiness evidence, recruited pilot cohort, production staff roster/drills, measured pilot outcomes, or post-launch review. |
| Production infrastructure | Local Compose, a provider-neutral production blueprint, fail-closed GAP-002 environment, GAP-003 managed-PostGIS, GAP-004 pilot-city, GAP-005 operations-governance and GAP-006 map/routing/navigation validators, health checks, rate limits, explicit database-pool bounds and telemetry, authenticated metrics, bounded rotating JSON logs, hardened Prometheus/Alertmanager/Loki/Alloy/Grafana, immutable metric/log dashboards, validators, and backup scripts exist. | All committed external-acceptance records are deliberately `NOT_STARTED`; there is no accepted production host, registry image, TLS ingress, DNS, secret manager, managed database/PITR, city/operator launch approval, production staff governance, promoted map/routing artifacts, hosted monitoring/log evidence, real pager/on-call roster, HA log store, or deployed rollback rehearsal. |

## Document map

| Area | Authority | Standing note |
| --- | --- | --- |
| Dated readiness assessment | [`readiness.md`](readiness.md) | Weighted source completion, requirement comparison and fresh versus historical verification. |
| Release baseline record | [`release_baseline.md`](release_baseline.md) | Reviewed candidate scope, local verification, immutable promotion requirements and rollback boundary. |
| Delivery workflow | [`workflow.md`](workflow.md) | Task contracts, executable checks, handoffs and evidence-based promotion. |
| Product mission and scope | [`product.md`](product.md) | Normative product contract; implementation does not prove market validation. |
| National operations and city rollout | [`operations.md`](operations.md) | Source workflows are broad; every real city gate remains evidence-based. |
| System boundaries and source of truth | [`architecture.md`](architecture.md) | Implemented architecture plus explicit provider/deployment boundaries. |
| Concrete repository structure | [`implementation.md`](implementation.md) | Current technical baseline and verification claims. |
| Delivery sequence | [`roadmap.md`](roadmap.md) | Source phases versus deployment acceptance. |
| Railway staging and release operations | [`deployment.md`](deployment.md) | Minimal topology, actual provider/account preflight, hosted verification, cost and safe shutdown. |
| Deployment gap register | [`gaps.md`](gaps.md) | Prioritized remediation and acceptance criteria. |
| Testing and acceptance map | [`testing.md`](testing.md) | Promotion gates from static checks and an executable 20-scenario simulated-persona baseline through real-city rollout. |
| Test execution control board | [`testing_execution_map.md`](testing_execution_map.md) | Entry/exit gates, executable evidence-index and T2 catalog rules, owners, stop rules and cohort progression from simulation to national replication. |
| Executable synthetic workloads | [`testing_workloads.md`](testing_workloads.md) | Bounded closed/open-loop passenger and driver HTTP write, four-phase capacity profiles, dispatch and cash-journey testing, safety guards, measurement limits and LOAD-01–12 progression. |
| Threat model and security tests | [`threat_model.md`](threat_model.md) | Trust boundaries, abuse cases, test packs and independent acceptance criteria. |
| Interaction and accessibility | [`design.md`](design.md) | Normative interaction rules; manual UX acceptance remains open. |
| Visual identity and UI waves | [`ui.md`](ui.md) | Approved identity and current implementation standing. |
| Detailed screen contract | [`extended_ui.md`](extended_ui.md) | Screen-level target and delivered operations modules. |
| HTTP contract | [`api.md`](api.md) | Implemented and target API conventions; OpenAPI remains runtime authority. |
| Identity and permissions | [`auth.md`](auth.md) | Mobile offline-code reset and backend session controls now exist; verified contacts, recovery issuance UX, privacy rights, and production recovery evidence remain. |
| Persistent data model | [`database.md`](database.md) | Logical model and migration-backed implementation through `20260908_0052`. |
| Driver participation | [`drivers.md`](drivers.md) | Driver, vehicle, credential, city application, and authorization contracts. |
| Ride lifecycle | [`rides.md`](rides.md) | Immediate, fixed-route-linked, and scheduled-handoff ride behavior. |
| Matching and fairness | [`matching.md`](matching.md) | Deterministic dispatch and aggregate fairness controls. |
| Tariffs and fare records | [`pricing.md`](pricing.md) | Versioned city economics and immutable snapshots. |
| Payment and settlement | [`payments.md`](payments.md) | Cash/manual transfer launch scope and deferred providers. |
| Security baseline | [`security.md`](security.md) | Implemented controls and required production evidence. |
| Graphical asset contract | [`graphic_assets.txt`](graphic_assets.txt) | Asset manifest and fallback rules. |

The `.tex` and `.pdf` report/pitch artifacts are communication outputs. They are
not normative and must be regenerated when the status summary materially changes.

## Reading order for implementation work

1. Read this file and [`roadmap.md`](roadmap.md) for the current milestone,
   next task and exit evidence. Use [`union_demo.md`](union_demo.md) for A journeys;
   [`gaps.md`](gaps.md) and [`testing.md`](testing.md) for real-world release gates.
2. Read [`roadmap.md`](roadmap.md) and [`implementation.md`](implementation.md)
   to confirm scope and delivery gates.
3. Read [`architecture.md`](architecture.md) and the relevant domain document.
4. Read [`api.md`](api.md) and [`database.md`](database.md) for external and
   persistent contracts.
5. Read [`security.md`](security.md), [`threat_model.md`](threat_model.md),
   [`design.md`](design.md), [`ui.md`](ui.md),
   and the relevant [`extended_ui.md`](extended_ui.md) section when data, security,
   or user experience changes.

## Documentation maintenance rules

* Do not change a normative business rule merely to match convenient code.
* Do not label a source feature production-ready without the evidence listed in
  [`gaps.md`](gaps.md).
* Every migration-backed feature updates `database.md`, `api.md`, the owning
  domain document, and the roadmap standing in the same change.
* Every closed gap records the evidence location and audit date before its status
  changes.
* Generated OpenAPI and executable tests resolve implementation ambiguity;
  product and security documents resolve policy ambiguity.
