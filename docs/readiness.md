# TaxiMobile — Repository Readiness Assessment

**Source assessment date:** 2026-09-09. **Standing refreshed:** 2026-09-29.
**Assessment base commit:** `f85417bcc8b432477fd88e87f5bd557a43898447`.
**Current verified candidate:** `004bfb26b143b075fcc0f78d293f675fc75882f1`.
**Migration head:** `20260908_0052`.

## Decision and percentage

**Estimated engineering implementation: 84%. Public/live-pilot readiness: blocked.**
The estimate measures the weighted source scope below. It is not elapsed effort,
test coverage, probability of success, or a forecast that 16% of the calendar time
remains. Integration and acceptance can take disproportionately long. Treat
roughly **75–90%** as a planning sensitivity range, not a statistical confidence
interval. The weights and ratings are this assessment's judgments, not approved
product priorities.

The [gap register](gaps.md) retains **19 P0 gates (GAP-001–019), none recorded as
deployment-accepted**, plus 18 P1/P2 gaps. Thus documented P0 closure is **0/19
(0%)**. This measures closure evidence, not absence of engineering work. There is
no meaningful aggregate percentage that permits an unresolved P0 to be averaged
away. The product owner retains launch, policy, visual, and architecture authority.

## Audit coverage and limitations

The inventory covered every project area: clients, backend, infra, CI, docs and
assets. The baseline inventory before the current staff-governance implementation
slice contained 922 project files: 373 client, 389 backend, 55 infrastructure, 74
asset, 27 documentation, two GitHub, and two root files. It included 23 backend
domain directories, 48 migrations, 110 backend test files and 59 Kotlin
`*Test.kt` files. Those baseline counts are retained only for audit orientation;
they are not a current file count or completion metric.

Inventory used `git ls-files --cached --others --exclude-standard`, deduplicated
and excluding generated `test-results`, `kotlin-js-store`, `node_modules`, and
pytest temporary directories. Ignored runtimes, build products, local databases,
secrets and IDE state were not treated as product implementation. Git reported an
unreadable `backend/.pytest_tmp_phase16_full/` directory; it is test debris outside
the assessed source. No files were deleted. The two existing PDFs were treated
as derived communication artifacts and rebuilt from their revised TeX sources.

Review combined documentation standing/requirements and gap sections, router and
worker wiring, critical ride/matching/pricing/payment/scheduling implementation,
migration constraints, client composition/gateways, tests and release scripts.
This is a repository-wide structural and targeted implementation review, not a
line-by-line security audit of all 922 files. The current immutable push and
pull-request CI runs were inspected on 2026-09-28; no hosted production service,
real provider account, device, legal record, bank statement or staffing roster
was inspected. Existing documentation's older test results remain historical
claims unless explicitly rerun below.

## Reproducible scoring method

Rate each engineering workstream from 0 to 4:

| Rating | Source criterion |
| --- | --- |
| 0 | Requirement only; no implementation path found. |
| 1 | Model, interface or scaffold only. |
| 2 | Material implementation, with a major required workflow absent. |
| 3 | Main workflow and tests present; meaningful source/integration gaps remain. |
| 4 | Defined core source path and meaningful automated tests present across its boundaries. This still does not certify deployment. |

`implementation_percent = sum(weight × rating / 4)`, with weights totaling 100.
The current numerator is 336 weighted rating points; `336 / 4 = 84%`.
Deferred card processing, pooled seats, recurring bookings and speculative scale
features are excluded. Missing verified identity, privacy workflows and payout
accounting are included because the gap register explicitly requires them.
Production service acceptance is tracked separately to avoid double-counting.

| Workstream | Weight | Rating | Contribution | Evidence and remaining source scope |
| --- | ---: | ---: | ---: | --- |
| Identity and recovery | 8 | 3 | 6.00 | `backend/src/taximobile_api/domains/auth/`, shared account/auth features; session controls and offline codes exist. Verified contact delivery remains absent (GAP-020). |
| Driver recruitment and eligibility | 8 | 4 | 8.00 | `domains/drivers/`, `domains/driver_applications/`, mobile onboarding, applicant portal, city authorization integration tests; real documents/licensing acceptance remains GAP-012. |
| Immediate rides and coordination | 10 | 4 | 10.00 | `domains/rides/`, `domains/ride_communications/`, shared rides features, `test_mvp_lifecycle.py`, `test_live_ride_concurrency.py`; six closed coordination signals, not general chat. |
| Matching and assignment integrity | 8 | 4 | 8.00 | `domains/matching/service.py`, `workers/matching.py`, migration 0048 and assignment/contention tests; source handles candidate locking, retry and active-ride uniqueness. |
| Pricing and immutable economics | 7 | 4 | 7.00 | `domains/pricing/service.py`, city pricing tests and financial snapshots; legal tariff approval remains external. |
| Payments and settlement | 8 | 3 | 6.00 | `domains/payments/`, cash/manual transfer/refund tests; earnings exist, payout periods, ledger and remittance do not (GAP-024). |
| Fixed routes and scheduling | 7 | 4 | 7.00 | `domains/fixed_routes/`, `domains/scheduled_bookings/`, route/acceptance/handoff integration tests and client gateways; field punctuality remains unaccepted. |
| Passenger/driver mobile | 10 | 3 | 7.50 | `TaxiMobile/shared/`, `androidApp/`, `iosApp/`, native source sets and shared tests include release identity plus preflight/upgrade UI; account/privacy gaps, signed old/current artifact testing and approved release support remain. Physical UX is a separate acceptance gate. |
| Applicant/operations web | 7 | 3 | 5.25 | `TaxiMobile/webApp/src/webMain/` and `webTest/`; operational modules, staff maker-checker queue and release preflight gate exist, while old/current hosted-release switching, complete browser-journey E2E and field accessibility acceptance remain. |
| Maps, places, navigation and delivery | 6 | 3 | 4.50 | Routing/places/push adapters, MapLibre, native location and notification relays; accepted Arabic narration and full operational delivery/fallback integration remain. |
| Support and safety | 5 | 3 | 3.75 | Support/safety/case-alert/retention domains and workers; incident operations and cross-store evidence remain incomplete. |
| City control plane and governance | 5 | 3 | 3.75 | Markets/administration domains, operations scope/readiness UI, durable staff maker-checker decisions and two-admin continuity exist. Roster ownership, recertification, break-glass controls and broader high-impact dual control remain (GAP-022). |
| Privacy rights and data lifecycle | 4 | 2 | 2.00 | Case/document retention, holds and account containment exist; self-service deletion/export and full cross-store erasure remain (GAP-021/030). |
| Analytics | 2 | 3 | 1.50 | Analytics domain, worker and web views; event-quality/evolution and operational threshold governance remain (GAP-037). |
| Deployment and observability tooling | 3 | 3 | 2.25 | `infra/deploy/`, backup/restore/verification scripts, worker readiness and monitoring; production provisioning/recovery evidence absent. |
| CI, supply chain and release tooling | 2 | 3 | 1.50 | `.github/workflows/ci.yml`, contract and provenance validators; complete artifact lifecycle/immutable remote evidence remain. |
| **Total** | **100** | | **84.00** | **Engineering scope only.** |

Paths beginning `domains/` or `workers/` are relative to
`backend/src/taximobile_api/`; integration test filenames are under
`backend/tests/integration/`. Ratings are capped at 3 when the workstream still
has an identified implementation gap, even if many individual modules are mature.
Several rows cover interacting layers; the weights partition this assessment's
engineering scope rather than counting each feature once per file.

## Requirements compared with implementation

| Requirement authority | Finding | Consequence |
| --- | --- | --- |
| `architecture.md`, `implementation.md` | Shared Kotlin/Compose clients, dedicated browser roots, FastAPI modular monolith and PostgreSQL authority match the approved architecture. | Keep the existing architecture; no new service framework is justified by this audit. |
| `rides.md`, `matching.md`, `database.md` | Ride locking, candidate revalidation and partial unique active-driver index are implemented. Migration 0048 refuses conflicting historical data. | Rehearse migration on a production-like copy; never silently repair conflicting rides during upgrade. |
| `pricing.md`, `payments.md` | Decimal fare components and immutable policy references exist; ride completion and payment settlement are separate. | A receipt/earning row does not establish real cash custody or operator payout. |
| `product.md`, `drivers.md`, `operations.md` | City-scoped recruitment, coherent configuration, service enablement and driver authority exist. | Activating a software city state cannot validate a license, legal authorization or uploaded readiness evidence. |
| `api.md`, `auth.md`, `security.md` | Mounted routes, scoped roles/MFA and client HTTP operations align in current contract checks. | Method/path validation does not validate every payload or authorization branch; keep negative and integration tests. |
| `design.md`, `ui.md`, `extended_ui.md` | Source implements role-specific map-first UI, localization and RTL; source tests cover fallbacks. | Accessibility and real-device journey acceptance are still needed. Generic screen specifications must not expose unavailable services. |
| `testing.md`, `testing_workloads.md`, `threat_model.md` | Executable test phases, bounded workloads and security packs exist. | Historical local results cannot substitute for clean-candidate CI, realistic capacity, independent security review or a staffed field exercise. |

## Documentation drift found

1. `README.md` advertised head 0048 but its backend/document-map rows still said
   0046. Corrected to 0048. Historical 0046 test narratives are preserved as history.
2. GAP-003 requested a 0046 rehearsal although 0048 is current. Updated its
   forward-looking acceptance target; old backup evidence is not relabeled.
3. The TeX report was previously reconciled for browser and driver-location
   standing, but it now predates migration 0049 and the staff maker-checker queue.
   Treat the generated report and briefing as dated derived artifacts until their
   sources are deliberately revised and rebuilt; this live readiness record and
   the domain documents are authoritative for the current source tree.
4. `TaxiMobile/README.md` previously said operations production access awaited
   MFA and cookie/CSRF implementation. Its setup text now matches current auth
   source and `docs/auth.md`: those controls exist, while hosted CSP, enrollment,
   deployment review and acceptance remain open.
5. The extended UI introduction's broad “real-time driver discovery” wording can
   be mistaken for pre-assignment supply browsing. Clarified it using the existing
   `product.md` supply-privacy rule, without adding a new product decision.
6. “CI-wired” previously described only a working-tree workflow definition. The
   complete push and pull-request workflows now pass at immutable commit
   `004bfb26b143b075fcc0f78d293f675fc75882f1`; this still is not release approval.

## Verification performed for this assessment

| Check | Recorded result through 2026-09-29 | Boundary |
| --- | --- | --- |
| Backend `python -m pytest tests/unit tests/api` | **699 passed**, 173 dependency deprecation warnings, 45.52 seconds | Earlier focused check; superseded for backend breadth by the fresh full-suite row below. |
| Full backend on fresh isolated PostGIS through `20260908_0052` | **992 passed**, zero failures/errors/skips, 175 dependency warnings, 1,344.70 seconds | Fresh current-worktree JUnit plus bounded T3 metadata/report evidence includes client compatibility, explicit pool bounds/exhaustion, staff dual control, legacy-admin retirement telemetry, security-incident operations, named lock/race/worker recovery and database reconciliation. One stale clone from an older interruption was removed; zero remained and temporary local `CREATEDB` was revoked. This is not capacity, immutable CI, hosted, provider, device, backup/restore or user acceptance. |
| Mobile/backend contract validator | **83 HTTP + 1 WebSocket operations passed** | Includes the command-free client compatibility preflight; source operation/path agreement, not device/provider delivery. |
| Focused staff/control-plane PostGIS integration | **28 passed** through `20260907_0049`; the four new staff scenarios and migration downgrade/re-upgrade also passed separately | Covers national scope, city pricing, fixed routes, staff request/replay/decision, revocation, continuity and bounded quorum bootstrap. |
| Focused city-rollout dual control | **17 unit contract cases passed locally**; the updated migrated two-city journey is delegated to fresh-PostGIS CI | Configuration approval and readiness decisions reject the configuration submitter, while a city-manager maker/platform-admin reviewer path remains covered. This is source enforcement only; no real city, operator, legal approval or pilot authorization is claimed. |
| Focused security-incident source/PostGIS | **18 dedicated cases** through `20260908_0052` (16 unit/static and two migrated API/database cases) | Adds initial lead assignment, eligible exact-market reassignment, ineligible refusal, concurrent one-winner serialization, idempotent replay, version authority, generated timeline facts and assignment-history mutation refusal to the existing lifecycle/postmortem/deadline coverage; not an authoritative roster, hosted receiver or staffed drill. |
| Operations web JS and Wasm browser suites | **57 passed per target** | Adds responsibility-input/history decoding to the seven earlier security-incident permission/lifecycle/input/version/postmortem tests; it does not prove staffed browser journeys or accessibility. |
| Static web compatibility loader | **6 runtime scenarios passed** | Executes supported/update/forced-upgrade/error/retry/local-origin behavior and proves client headers remain scoped to the exact API origin and `/api/v1/` path; this is not a hosted-browser or ingress test. |
| Operations web production distributions | **JS and Wasm production distributions built** | Local optimized artifacts exist for source verification; this is not the packaged compatibility release, hosted CSP/TLS proof, browser E2E, or an immutable signed artifact. |
| Web/backend contract validator | **112 HTTP operations passed** | Includes the fail-closed static compatibility preflight, six staff-request and nine security-incident client operations, with the responsibility path selector restricted to four values; does not prove full browser journeys. |
| Infrastructure script unit tests | **167 passed** | Includes validator/provenance/package behavior, strict web release identity, generated API/migration/permission inventory, executable T0–T10/T2 persona, fail-closed T3 backup/restore, balanced T4 laboratory-map, GAP-002 environment, GAP-003 managed-PostGIS, GAP-004 pilot approval, GAP-005 operations-governance and CI-wiring mutation coverage. |
| Bounded T2 simulated-persona baseline | **20 scenarios / 60 exact tests passed** | Source-level synthetic authority and state-machine coverage only. The report refuses T2/deployment acceptance and identifies missing adversarial, durable reconciliation, minimization and sign-off evidence. |
| Bounded T3 system baseline | **992 tests and all six required evidence kinds passed locally** | JUnit, secret-free database metadata and a guarded logical restore reconcile 81 public tables/8,511 aggregate rows at migration 0052. The target and dump were removed. Evidence completeness is true, but the dirty-workspace snapshot has no engineering sign-off or ordered phase acceptance; T3 and deployment acceptance remain false. |
| T4 laboratory map | **56 reviewed cases; 0 executed** | Exactly eight cases cover each required evidence kind and source targets/locales/browsers are cross-checked. The template is deliberately `NOT_STARTED`; no device, browser, accessibility, failure or crash acceptance is inferred. |
| Bounded T4 browser boot smoke | **8/8 local scenarios passed** across Chrome 152 and Firefox 155 | Packaged-release preflight, blocked/boot branch selection and screenshot retention passed. Safari, authenticated critical journeys, accessibility/RTL, console/source-map review, hosted headers and independently firewalled browser egress remain absent; zero complete T4 catalog cases and no phase/deployment acceptance are claimed. |
| GAP-002 production environment inventory | **Schema/template and ten focused validator cases passed; status `NOT_STARTED`** | The validator requires three isolated environments, 12 reviewed service boundaries, exact TLS origins, digest-pinned core images, private infrastructure, rotation/recovery/cost records and five approvals. No provider or hosted target has supplied that evidence, so GAP-002, T5 and deployment remain unaccepted. |
| GAP-003 managed PostGIS evidence | **Schema/template and 14 focused validator cases passed; status `NOT_STARTED`** | The validator requires private encrypted PostgreSQL 16/PostGIS compatibility, separated authority, current-head migration, capacity reserve, automated backups/PITR, restore/failover within RPO/RTO, retention-expiry proof and four approvals. No managed service has supplied those facts, so GAP-003, T5 and deployment remain unaccepted. |
| GAP-004 pilot-city approval evidence | **Schema/template and 19 focused validator cases passed; status `NOT_STARTED`** | The validator binds one real city/operator to an active configuration, cash-inclusive scope, public terms, accountable functions, bounded exposure, ten independent readiness decisions and six approvals. It supports an explicitly approved on-demand/fixed-route/scheduled scope without silently enabling one. No owner has supplied the city, legal operator or approvals, so GAP-004, T6 and deployment remain unaccepted. |
| GAP-005 operations identity/governance evidence | **Schema/template and 16 focused validator cases passed; status `NOT_STARTED`** | The validator requires roster/JML authority, three distinct platform-admin quorum duties, explicit sensitive-duty separation, reviewed TOTP/recovery custody for every assigned account, access-review/leaver bounds, eight drills, audit references and four approvals. No production accounts, roster owner or human drill evidence exists, so GAP-005, T5 and deployment remain unaccepted. |
| Remote immutable candidate CI | **Complete push and pull-request workflows passed at `004bfb2`** | Push run 36573648020 passed dependency submission; PR run 36573658223 passed dependency review. Backend/fresh PostGIS, mobile, web, documentation/provenance, wrapper integrity and both iOS jobs were green. This does not supply independent review, branch protection, signed distribution artifacts, a registry digest or release approval. |
| Mobile script unit tests | **38 passed** | Includes privacy-bounded Android registration/login evidence contracts and iOS Keychain source guards that reject impossible native casts, split token writes and unchecked status handling. No phone was attached and no physical-device result is claimed. |
| Android role release verification artifacts | **Passenger and driver 1.0.0 APKs built and manifest-verified** | Distinct package IDs, versions, sizes and SHA-256 hashes are recorded. The manifest is intentionally `distribution_eligible=false` because signing, Firebase/Crashlytics and physical-device acceptance are absent. |
| iOS role release verification artifacts | **Kotlin production/test sources compiled; Passenger and Driver Release simulator applications linked and evidence-bound at `de69829a`** | The exact 14-package graph was restored from the committed lock, automatic resolution stayed disabled, and both immutable runs passed. MapLibre Compose upstream issue #824 still prevents Gradle native-test linking, so no iOS native-test execution, signed archive, provider configuration, physical-device result, or deployment acceptance is claimed. |
| Documentation validator | **Passed before and after edits** | Links, standing blocks, gap/test sequences and migration head. |
| Shared JVM suite | **190 passed**, zero failures/errors/skips | Fresh JVM execution adds atomic token-envelope corruption cases and protected-storage failure behavior, including revocation of newly issued login/refresh sessions after a failed save. iOS remains non-executable on Windows. |
| TeX/PDF build and visual checks | **Passed: 18-page report and 36-slide briefing**, compiled with pdfLaTeX, rendered and visually inspected | No overfull boxes, undefined references or TeX errors in final logs. MiKTeX reports its local update-check notice. |

The latest complete backend test execution is **992 full fresh-PostGIS tests at 0052**,
with separate focused migration/control-plane evidence for the staff slice. The
records also report **190 shared JVM tests**, plus
Android and JS/Wasm verification. No iOS device, signed release, hosted load,
provider acceptance, managed encrypted backup/PITR, live passenger, or real-money
test is claimed here.
Deprecation warnings are maintenance work, not failures caused by this change.

## Updated deliverables

The current implementation includes migration 0049 staff dual control and now
adds migration 0052, which gives security incidents four closed responsibility
types, one active assignee per type and append-visible reassignment tenure. The
API validates an exact active market-authorized responder, and the protected web
workspace can review and assign responsibility without adding a user-search
surface. It also updates the governing API, database, operations, security, gap
and test records. [The technical report](taximobile_technical_report.pdf) and
[the technical briefing](taximobile_pitch_deck.pdf) remain dated derived artifacts
and were not regenerated by this slice. Existing unrelated uncommitted work was
preserved.

## Next work, in dependency order

1. **Establish a reproducible candidate:** review the dirty source and untracked
   migrations/assets; produce a clean checkout, complete CI and artifact hashes
   (GAP-001/033/036). Do not discard local work to manufacture a clean status.
2. **Resolve policy-dependent software:** verified contacts/recovery, privacy
   rights, staff roster/recertification and break-glass governance, payout
   accounting and retention decisions (GAP-020–024/030). Record decisions in
   owning domain docs before implementation; this audit does not choose them.
3. **Accept isolated staging and providers:** hosting, current-head restore,
   maps/geocoder/routing, push, protected documents, monitoring and payment
   procedures (GAP-002/003/006/008–010/012/015).
4. **Close device, browser, security and capacity gates:** signed candidate
   artifacts, representative Arabic/French/English journeys, failure recovery,
   independent review and production-like workloads (GAP-007/013/014/016/018/025/026).
5. **Rehearse a real operating organization:** city/operator approval, scoped
   staff enrollment, safety/pager shifts, money controls, incident/rollback drills
   and explicit pilot thresholds (GAP-004/005/011/017/019/031/032).
6. **Promote through T7–T10 only with accepted evidence:** owner-approved bounded
   field validation, pilot, public city launch and then second-city expansion.

Use [workflow.md](workflow.md) for task handoffs and commands. Use [gaps.md](gaps.md)
for detailed closure criteria. This assessment summarizes their implications and
does not replace either the domain requirements or the release vetoes.
