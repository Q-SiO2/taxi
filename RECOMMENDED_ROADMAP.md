# TaxiMobile — Recommended delivery roadmap

**11 October 2026. Recommendation, not deployment approval.** Read with [the audit](C:/Users/Q/Projects/AUDIT_REPORT.md). Baseline is HEAD `2835c8a` plus existing uncommitted work. Keep Python/FastAPI/PostGIS and Compose mobile; use current web operations/applicant surfaces for the pilot. No application changes or migrations were made in producing this roadmap.

## Milestones and assumptions

**Milestone 1: deployable pilot.** A reviewed, signed application and accepted service environment used by a bounded real cohort in one authorized city. It includes legitimate driver onboarding, working booking/dispatch, accurate location under the approved operating model, trip completion, cash records, support, recovery and privacy handling. A successful emulator demo is a preceding rehearsal, not this milestone.

**Milestone 2: high-quality first-city public release.** Android and iOS role applications plus operations have accepted visual/accessibility quality, reliable service delivery, support and recovery, distribution approval and legal authority. National deployment and every optional feature are not prerequisites for excellence in one city.

Planning assumptions: two experienced full-time engineers, one primarily mobile/KMP/native integration and one backend/platform; 0.25–0.5 product-design FTE during design work and 0.5 QA FTE during stabilization; an accountable operator/legal owner outside engineering; access to macOS/Xcode and representative Android/iOS devices; roughly five productive days per person-week (PW). Engineers can review each other's work and preserve domain authority. Estimates are work-package judgments, not derived from commit counts or AI coding speed. Re-estimate after the first two weeks of verified work.

External approval, entity/bank/developer-account verification, procurement and driver recruitment run in parallel. Their delays are not included in engineering time and cannot be assigned a reliable upper bound here. No roadmap date permits a P0 gate to be waived implicitly.

## Phase 0 — Set the pilot contract and review the candidate

**Engineering effort: 2–4 PW. Dependencies: owner/operator availability.** Start legal/provider work immediately alongside this phase.

Deliverables:

- Review and incorporate the existing 109 Git status entries deliberately; retain other work. Produce an immutable candidate and evidence manifest with review ownership.
- Reconcile stale gap claims with current code, especially immediate-offer location guarding and the iOS MapLibre test-link exclusion. Keep acceptance distinct from source implementation.
- Select the intended city, licensed operator, driver cohort, service/fare type, languages, operating hours and support responsibilities. Demo Casablanca is not an authorization.
- Decide whether the pilot is Android-only. If so, label its evidence accordingly; iOS remains a separate product obligation.
- Freeze pilot capabilities through existing city/configuration controls. Recommendation: immediate booking, direct cash, no wallet/card, no transfer custody and no scheduled services unless required by approved scope.
- Establish candidate test commands and environment ownership. The full PostGIS runner recreates test databases and runs migrations; execute only in the implementation/verification phase with appropriate authorization and isolation, not retroactively as part of this assessment.

**Exit evidence:** reviewed candidate, agreed scope, current CI and contract results, no unexplained source/document mismatch. GAP-001/033/034/036 guide evidence; this phase alone cannot close release acceptance.

## Phase 1 — Establish legal, data and operating feasibility

**Engineering contribution is included in backend/infrastructure work below; external elapsed time is independent.** Owner: operator with Moroccan legal/privacy/tax advice. Depends on the selected entity, city and service.

Obtain written confirmation of the applicable taxi-intermediation authorization path and legal entity; validate licensed driver/vehicle requirements, permitted service area, meter/fixed fare and fee rules, cancellation/receipt obligations and insurance coverage for app-dispatched trips. Set controller/processors, CNDP filings and foreign-transfer treatment, document/location/incident retention and user-right procedures. Decide who receives fare money and who invoices each charge; avoid inventing a wallet or payout promise.

Recruit a small licensed cohort with enough scheduled availability to test the proposed promise, and assign real support/safety/cash owners. Define what “available,” “arriving,” “payment recorded” and “support contacted” mean operationally.

**Exit evidence:** signed applicability/approval records for city, operator, fare, insurance, privacy and operations; no real transport before applicable authorization. GAP-004/005/011/017/019 and affected P1 obligations apply. The existing 19 P0 release gates remain authoritative.

## Phase 2 — Make the essential journey correct

**Mobile/device engineering: 5–8 PW. Backend/privacy engineering: 4–7 PW.** Depends on phase 0; legal decisions determine fare/data policy.

1. Preserve GPS acquisition time/age and accuracy through Android/iOS/shared/API boundaries. Refuse stale/future/invalid observations according to approved policy; prevent a cached observation from becoming fresh on transmission. Test source time versus receipt time and lock-wait outcomes.
2. Repair the new location-test fixtures (nonexistent `ServiceAreaStatus.RETIRED` and the database-geometry copy requiring absent Shapely), then verify the current acceptance-time location guard on fresh isolated PostGIS, including concurrent ingestion, expiry, missing/outside-area/future observations and one-winner assignment. Preserve established lock ordering. The retained 11 October focused report has two failures; a unit pass does not close them.
3. Rehearse the foreground-only driver model under phone lock, incoming call, navigation switch, revoked permission, slow network and long shift. If it cannot meet agreed service targets, document and approve bounded background tracking before implementation. Budget an additional 3–6 PW if that change is required; do not silently add it to pilot scope.
4. Verify command uncertainty, reconnect and session rotation on both roles: reload authoritative state after ambiguous responses; never display an invented assignment or settled payment. Keep automatic location/readback from blocking human ride actions.
5. Implement contact verification/delivery recovery for the selected mechanism, with throttling and abuse limits. Retain offline codes as a deliberate option, not the only untested recovery story.
6. Implement account deletion initiation, external deletion request route, authenticated access/export and backend processing; enforce documented retention exceptions and cross-store deletion, including document storage and processor obligations.
7. Verify completion, pending-cash recovery and idempotent cash settlement through visible driver/rider states. Define reconciliation and receipt responsibility. If operator-held money or driver deductions are enabled, implement and test the required ledger/remittance controls before those capabilities ship.
8. Ensure licensed-driver verification, suspension, expired credentials and city scope actually constrain every dispatch/acceptance path; map document scanner/storage failures into recoverable onboarding states.

**Exit evidence:** API/database/native tests plus a candidate-bound two-role journey under adverse conditions. Code correctness is necessary; provider and field acceptance still follow. GAP-007/009/010/012/020/021/024/028/030.

## Phase 3 — Polish the complete rider and driver journeys

**Engineering: 4–6 PW, with product designer input.** Starts after the phase 0 scope and stable journey contracts; can overlap phase 2.

Keep approved navy/gold branding. Correct 2.22:1 gold-on-white text contrast, make navigation chrome compact without shrinking touch targets, constrain long labels, remove technical identifiers and unnecessary maneuver text from the quote, and make the next action visually dominant. Preserve clear safety access and explain unavailable actions.

Refactor only the affected PassengerHome/DriverHome/coordinator boundaries into coherent journey components. Apply the intended Arabic typography centrally; verify RTL, mixed phone/amount/address strings, French expansion, keyboard, safe areas, large text, TalkBack/VoiceOver, and reduced motion. Prefer clear state and response feedback to ornamental animations.

Create an approved screen/state reference set and automated visual fixtures. Review at least: registration/recovery, location denied, pickup/destination search, lawful quote, no supply, matching/cancel, assigned/arrival, pickup problem, active trip, completion, unpaid cash, receipt/history, offline/reconnect, expired session and blocked driver.

**Exit evidence:** design owner approval of rendered references; representative users complete tasks without developer coaching; no clipping or hidden primary action at tested sizes; contrast and accessibility checks pass. Frame/startup targets are agreed before measuring release builds. GAP-013/014/025/026.

## Phase 4 — Provision and accept staging/providers

**Engineering: 3–5 PW.** Depends on data-region/storage decisions and candidate review; overlaps phases 2–3 where contracts are stable.

Provision managed PostGIS and always-on API/worker using the existing architecture. Select one routing engine and accepted graph, a lawful tile/style/geocoder source and tested Moroccan address dataset. Configure FCM/APNs per role and production signing identities. Confirm actual public TLS/DNS and private service boundaries, runtime/migration privileges, secret custody/rotation and staff MFA recovery.

Implement a durable private document boundary usable by API and retention workers; test scan rejection, scoped reads, encryption-key recovery and deletion. A local filesystem adapter cannot be assumed to work across arbitrary PaaS replicas. Verify database-plus-documents backup restoration, logs/metrics/crash collection, redaction, externally reachable alerting and deployment rollback.

**Exit evidence:** working providers in isolated staging, reconciled restore with measured RPO/RTO, immutable image/app identities, alert received by a named responder, approved cost/region assumptions. GAP-002/003/006/008/010/012/015/018. Provider accounts and deployments were not created by this audit.

## Phase 5 — Stabilize one exact candidate and prepare pilot release

**Engineering: 4–7 PW stabilization + 2–3 PW pilot packaging/rollout.** QA effort runs alongside. Depends on phases 1–4 for a real pilot.

Run fresh migration-chain and transaction/concurrency verification in isolated PostGIS, browser tests and complete staff/applicant journeys. Revisit MapLibre native linking on macOS using the pinned artifact and a compatible candidate fix; restore actual iOS native test execution rather than counting simulator links as test runs. Run signed release apps on low/mid-range Android and target iPhones as applicable. Measure startup, frame time, memory, battery, GPS quality, reconnect and notification delivery under real networks.

Test no-supply, expiring offers, duplicate taps, simultaneous acceptance, crash/restart, lost responses after committed writes, token refresh/revocation, push denial, stale location and a payment still pending after trip completion. Verify unauthorized cross-city/operator access and sensitive-data minimization. Use production-like load tied to the pilot cohort and headroom; confirm database pool and outbox lag remain within agreed bounds.

Complete independent security review, store/privacy disclosures, deletion web page, reviewer access, artifact signing and protected release promotion. Staff the support/safety roster; rehearse reconciliation, account containment, service pause, provider failure, rollback and restore. Use synthetic rehearsal until the real-world authority gate permits field participation.

**Milestone 1 exit:** every applicable P0 gate accepted by its owner, affected P1s closed, signed candidate deployed under explicit owner approval, and bounded users/driver cohort with stop conditions. Android-only acceptance must not be represented as iOS acceptance.

## Phase 6 — Learn from pilot and reach public-release quality

**Additional engineering: 20–32 PW beyond the 24–40 PW pilot baseline.** Approximately 10–16 additional engineering calendar weeks with two engineers; actual overlap/field feedback affects elapsed time.

Use pilot data to correct address/dispatch failures, missed offers, confusing controls, cancellations, support response and cash reconciliation. Complete both mobile platforms and accessibility/browser coverage, legal retention operations, independent review follow-ups, backup/failover and old/new client compatibility. Establish review ownership, reproducible build support, dependency maintenance and incident/runbook training.

Do not react to initial adoption by adding a new architecture. Confirm the fundamental service meets agreed pickup reliability and support promises. Expand only after the first city sustains its targets, an accountable operator approves, and the next city's authorization/tariff/provider rules are independently verified. A React operations redesign can be evaluated here if measured browser/accessibility maintenance cost warrants it.

**Milestone 2 exit:** high-quality public candidate plus store/legal/operator approvals, support capacity, sustainable per-ride economics and proven recovery. National rollout is a subsequent decision.

## Scope classification by journey

| Journey | Must work for the pilot | Acceptable simplification | Defer |
|---|---|---|---|
| Rider onboarding | Identity, recovery, clear consent, deletion request | One approved verified contact channel | Social login, promotions |
| Driver onboarding | Actual licensed-driver/vehicle checks, city scope, expiry, suspension | Staff-assisted review of a small cohort | Automated document OCR/scoring |
| Pickup/destination | Valid points/addresses, permission fallback, service boundary | Limited accepted service area and landmarks | Nationwide place coverage |
| Booking/dispatch | Server quote, private offer, acceptance, expiry, no-supply, cancellation | One approved service type | Pooling and complex optimization |
| Trip status/location | Honest freshness and state, permitted tracking model, recovery | Explicit foreground operating conditions only if field-accepted | Unbounded tracking/history |
| Communication | Current six-code coordination plus staffed exception handling | No general chat if real tasks remain solvable | Free-text chat/VoIP without demonstrated need |
| Completion/payment | Final approved fare, separate completion/settlement, cash dispute and receipt | Cash directly to driver; approved zero operator fee if selected | Card/wallet and automated payouts |
| Administration/support | Scoped review, containment, case escalation, audit, reconciliation | Existing console with trained staff | New React console, advanced analytics |
| Safety/privacy | Real response path, minimal collection, rights/retention handling | Bounded hours/cohort with explicit responsibility | Nothing essential can be replaced by a disclaimer |

## Effort, calendar scenarios and migration comparison

Pilot baseline sums to **24–40 engineering PW**: candidate 2–4, mobile/native 5–8, backend/privacy 4–7, UI 4–6, infrastructure 3–5, stabilization 4–7, pilot packaging 2–3. Public-release total is **44–72 PW**. Design/QA/operator/legal work is additional; calendar estimates assume their availability. Overlap means phases are not sequential calendar blocks.

| Architecture | Pilot engineering PW | Public total engineering PW | Realistic calendar with two engineers | Main additional risk |
|---|---:|---:|---|---|
| A: retain stack | 24–40 | 44–72 | Pilot 12–20 weeks; public 22–36 weeks total | Native/provider/field acceptance |
| B: React Native/Expo mobile | 36–60 | 60–92 | Pilot 18–30; public 30–46 weeks total | Mobile parity, native reintegration and repeat validation |
| D: retain mobile, replace web with React now | 28–48 | 52–80 | Pilot 14–24; public 26–40 weeks total | Staff/applicant scope, auth/MFA and decision UX parity |
| C: browser-only for full taxi product | Not a comparable viable baseline | Not a comparable viable baseline | No credible like-for-like schedule | Reliable driver background/native lifecycle requirement remains |
| C supplemented with a native driver runtime | 40–64 | 64–100 | Pilot 20–32; public 32–50 weeks total | Becomes a hybrid project; two frontends and native integration |

These ranges do not claim a completed estimation workshop for every feature. B includes an estimated 12–20 PW increment for mobile parity/integration before pilot; D 4–8 PW for pilot web parity. Full national feature parity would add work. A familiar React Native team might reduce that increment; a Kotlin-only team would increase it. Decide with a complete-journey spike if staffing facts contradict these assumptions.

| Scenario | A pilot candidate | A public candidate, total | Conditions |
|---|---|---|---|
| Best case | 8–10 weeks | 16–20 weeks | Existing uncommitted work verifies quickly; foreground model accepted; service/fare fits current code; experienced team, providers and legal decisions ready; tightly bounded scope |
| Realistic planning baseline | 12–20 weeks | 22–36 weeks | Work packages above, two engineers plus design/QA, ordinary integration rework |
| Adverse | 24–36+ weeks | 40–60+ weeks | New background model, meter/fare changes, native library problems, provider/storage changes or field failures |

Best case relies on reduced remaining effort discovered in phase 0, not on pretending 40 PW can always fit into eight weeks. With one engineer, roughly double engineering elapsed time and allow further context-switching; part-time work scales with actual availability. External legal refusal can stop launch rather than merely extend a date.

### Cost model

Use your actual fully loaded weekly engineering rate **R**: pilot engineering cost is `24R–40R`; public total `44R–72R`. React Native pilot is `36R–60R`. At an **illustrative**, non-market-quoted USD 1,500/PW, A is USD 36k–60k pilot and USD 66k–108k public total; B is USD 54k–90k pilot and USD 90k–138k public total. Substitute actual employment/contract rates. These figures exclude design/QA, devices/macOS equipment, legal/accounting/insurance, recruitment, support staffing and taxes.

Allow approximately USD 150–400/month for the small pilot service footprint and USD 300–1,000/month for an initial public footprint, then quote actual usage/availability/region requirements. SMS and payment-provider costs require local contracts. Apple membership is published at USD 99/year and Play registration at USD 25 once; local terms may differ. All architecture options retain most of the same backend/provider costs. A cheap VM or free frontend hosting is not a total operating budget. Sources and limitations are in the audit.

## Critical path and first two weeks

The critical path is: **approved operating/fare/data model → corrected and validated core journey → accepted providers/storage/signing → device and staffed failure tests → owner-authorized pilot → measured polish/reliability fixes → public approval.** Contact authorities and resolve the operator now; those dependencies cannot be compressed by faster coding.

During the first two weeks, I would complete candidate review, prove the cached-location defect with a regression, validate the newest acceptance guard, nominate the legal/operator owner and submit precise questions, freeze the pilot scope, approve rider/driver visual references, and reproduce the iOS native linking exception on macOS. Record actual effort and remaining uncertainties, then replace these broad estimates with a candidate-specific plan.

Stop the pilot or refuse promotion for incorrect assignment/fare, stale location misrepresented as current, failed settlement reconciliation, unresolved access/privacy failures, unstaffed safety response or absent authority. The operator must approve numerical service/quality thresholds before field testing; metrics cannot be chosen afterward to make a run pass.

**Decision:** finish and validate the existing architecture. Reconsider only when a measured complete-journey comparison, an essential unrepairable platform dependency, or an unavailable sustaining team changes the economics—not because a different framework makes attractive demo screens easier.
