# TaxiMobile documentation

This directory is the product, architecture, security, and delivery authority for
TaxiMobile. It describes both the intended system and the software currently in
the repository. Those are not the same kind of statement.

## Current project standing

**Source assessment date:** 2026-09-09. **Standing refreshed:** 2026-09-28.

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
The latest full isolated-PostGIS regression through migration 0052 passed 992 backend
tests with zero failures, errors or skips; that result remains historical local
evidence. Immutable commit `de69829a649715ad7768756e285fedfde2fa846a` now passes
the complete push and pull-request workflows, but GAP-001 remains open because
independent review, protection, signing, registry digest, and release approval are
absent. The local regression includes the focused
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
| Passenger and driver mobile | Shared Android/iOS source, role-specific release identity and compatibility preflight, maps, rides, payments, support/safety, fixed routes, scheduling, recruitment, offline-code recovery, active-session controls, and password change are implemented. The immutable `de69829a` push and pull-request runs produced limitation-marked Android/iOS manifests and linked both iOS Release simulator apps. | MapLibre issue 824 still prevents native iOS test linking. Approved support/deprecation policy, intentionally obsolete signed-build testing, verified contact ownership, physical Android/iOS matrix, signed store artifacts, production Firebase/APNs, accessibility, network-loss, navigation, and crash-symbolication acceptance are open. |
| Public applicant and operations web | JavaScript and Kotlin/Wasm sources, release identity/preflight gate, protected operations authentication, staff maker-checker queue, city control plane, recruitment, pricing, payment, fixed-route, scheduling, case, security-incident, audit, and analytics modules are implemented. Immutable `de69829a` CI passed static preflight, both browser targets, compatibility packaging without maps, and clean-source manifest binding. | Old/current hosted-release switching, full browser E2E, production CSP/hosting, accessibility/RTL, authoritative staff/incident rosters, protected-document browser acceptance, and production operations-account enrollment remain open. |
| Backend and database | FastAPI modular monolith, six-surface release compatibility enforcement, eight worker loops, PostGIS schema through migration `20260908_0052`, scoped operations APIs including transactional staff dual control and security-incident responsibility/postmortem coordination, mobile recovery/session-control APIs, and local unit/API/integration coverage are implemented. | Approved release policy/drill, managed PostGIS, production migration rehearsal, encrypted backup/PITR, staging restore, capacity/soak, high availability, authoritative duty rosters, staffed incident drills, and production incident evidence are open. |
| Maps, places, routing, push, and crash reporting | MapLibre composition, normalized place search/reverse lookup with a fail-closed Nominatim-compatible adapter, Valhalla/GraphHopper adapters, FCM/APNs wiring, and Crashlytics release boundaries exist. | No production style/tile or geocoding source, accepted data/license and multilingual place benchmark, accepted routing graph, required-language narration matrix, Firebase credentials, or controlled device delivery/crash proof is recorded. |
| Payments | Cash, manually reconciled bank/M-Wallet transfer claims, versioned recipients/capabilities, refunds, and immutable financial snapshots exist. | Real recipient verification, controlled transfers/refunds, reconciliation staffing, statement fidelity, cash controls, and payout/settlement operations remain open. CMI/card is deferred. |
| National rollout | City/operator/configuration models, scoped grants, MFA, readiness gates, analytics, emergency pause, and repeatable rollout workflows exist. | No city has supplied legal/operator approval, real readiness evidence, recruited pilot cohort, measured pilot outcomes, or post-launch review. |
| Production infrastructure | Local Compose, a provider-neutral production blueprint, fail-closed GAP-002 environment and GAP-003 managed-PostGIS evidence validators, health checks, rate limits, explicit database-pool bounds and telemetry, authenticated metrics, bounded rotating JSON logs, hardened Prometheus/Alertmanager/Loki/Alloy/Grafana, immutable metric/log dashboards, validators, and backup scripts exist. | Both committed provider records are deliberately `NOT_STARTED`; there is no accepted production host, registry image, TLS ingress, DNS, secret manager, managed database/PITR, hosted monitoring/log evidence, real pager/on-call roster, HA log store, or deployed rollback rehearsal. |

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

1. Read this file, [`gaps.md`](gaps.md), and [`testing.md`](testing.md) to
   understand current standing and the required evidence path.
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
