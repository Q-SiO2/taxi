# Real-world deployment and full functionality

## Active goal - 23 October 2026

Deliver an operable TaxiMobile service for an authorized first city and operator,
then promote it to guarded public release with the full documented launch scope.
Passengers, licensed drivers and staff must complete their work through signed
mobile releases and the hosted web portals against a supported production backend.
Completion requires observed device, provider, operational and real-world evidence,
not another synthetic demonstration or a larger test count.

This is the execution companion to [roadmap.md](roadmap.md), implementing its
B-01 through B-06 and C-01 through C-03 packages. [gaps.md](gaps.md) remains the
acceptance authority for GAP-001 through GAP-037; [testing.md](testing.md) owns
T0-T10 promotion. Domain documents continue to own business rules. R0-R12 below
sequence existing requirements; they do not create a competing definition of done.

26 October R6/R9 checkpoint: [passenger pagination](launch/scheduled-pagination.md)
passes its own full [CI 244](launch/scheduled-pagination-ci-terminal-20261026.json).
The subsequent [cancellation review correction](launch/scheduled-cancellation-review.md)
passes its own [CI 246](launch/scheduled-cancellation-review-ci-terminal-20261026.json)
across all eight required jobs. The [driver review successor](launch/scheduled-driver-review.md)
is undergoing independent local/native verification. These source packets do not accept hosted, physical, operational
or field journeys. The Trial capacity stop and source-only continuation persist.

The [immediate-offer follow-up](launch/immediate-offer-review.md) now passes its
affected local shared/rendered/Android checks for elapsed timing, cancellation
and unavailable review. It still requires its own immutable native CI; scheduled
city-local timestamp presentation remains a distinct confirmed source follow-up.

## Starting point and interpretation of full functionality

[The board-alpha handoff](board-alpha-handoff.md) records native v23 / web v10,
two synthetic cash journeys and selected style/language observations. These are
retained regression evidence. They do not establish physical-device, iOS,
production provider, real-money, staffed support or public-launch acceptance.
Current application sources, deployed identities, Git state and GAP evidence
must be reconciled before deciding what needs implementation.

Full functionality means the capabilities below work end to end, with their
failure, permission, privacy and recovery states. Android, iOS, applicant web and
operations web are target release surfaces. A bounded pilot may expose a smaller
explicitly approved subset, but that cannot silently shrink this full-release goal.
Every exception needs an owner-recorded scope decision and unavailable UI/API
exposure; a provider adapter, screen, empty table or passing unit test is insufficient.

| Capability | Required operational result | Owning documents / gates |
| --- | --- | --- |
| Identity and accounts | Registration, applicable verification, login, MFA for staff, session refresh/revocation, recovery, restrictions, deletion/export and retention work without bypasses. | [auth.md](auth.md), [security.md](security.md); GAP-005, 020-022, 029-031 |
| Passenger on-demand | Actual pickup/place selection, server fare, request, private assignment, driver arrival, trip progression, cancellation/no-supply/unknown-result recovery, history and receipt. | [rides.md](rides.md), [matching.md](matching.md), [pricing.md](pricing.md); GAP-006-008, 018-019 |
| Licensed-driver lifecycle | City application, protected documents, review/correction, vehicle and authorization, eligibility restrictions, availability, offer accept/decline/expiry, ride execution and financial history. | [drivers.md](drivers.md), [operations.md](operations.md); GAP-005, 007, 012, 019 |
| Fixed routes | Staff publish valid services; passengers browse/book within documented capacity and eligibility; drivers execute; cancellations and money records reconcile. No pooling/segment-fare invention. | [product.md](product.md), [operations.md](operations.md), [api.md](api.md); B-03-B-06 |
| Scheduled bookings | Single-booking creation, allocation/commitment, deadlines, reminders, execution, cancellation and failure handling work across passenger/driver/staff. | [operations.md](operations.md), [rides.md](rides.md); B-03-B-06 |
| Maps, search and navigation | Approved real providers, service-area correctness, place discovery, route/reroute and honest EN/FR/AR guidance behavior, attribution and failure modes. | [architecture.md](architecture.md), [api.md](api.md), [gaps.md](gaps.md); GAP-006-008, 026 |
| Location and lifecycle | Field-accepted foreground/background/lock-screen behavior, permission denial, stale/inaccurate fixes, app/process death and network recovery preserve safe availability and trip authority. | [drivers.md](drivers.md), [extended_ui.md](extended_ui.md); GAP-007, 018-019 |
| Communication and notifications | Approved passenger-driver coordination and actual Android/iOS delivery for each critical event, including expiry, deduplication, privacy, acknowledgement and fallback. | [architecture.md](architecture.md), [api.md](api.md), [testing.md](testing.md); GAP-009, 023, 028 |
| Cash and manual transfer | Approved tariffs/fees, truthful collection, transfer review/reconciliation, corrections, disputes, audit and receipts; no client-authoritative payment status. | [payments.md](payments.md), [pricing.md](pricing.md); GAP-010 |
| Driver settlement | Approved operator obligations, driver balances, adjustments and settlement/payout accounting reconcile; no unsupported automated payout promise. | [payments.md](payments.md); GAP-024 |
| Safety and support | Real staffed triage, restricted case access, escalation, emergency disclosures, contact channels and incident handover are demonstrated. | [operations.md](operations.md), [security.md](security.md), [extended_ui.md](extended_ui.md); GAP-011, 023, 031 |
| National/city operations | Scoped operator/city/service-area configuration, tariffs, fees, recruitment, authorizations, routes, schedules, payment operations, analytics, audit and readiness workflows work on populated authorized data. | [operations.md](operations.md); GAP-004-005, 022, 029, 032, 035, 037 |
| Protected information | Driver files, access logs, retention, legal holds, erasure and rights requests work across all stores without public object exposure. | [security.md](security.md), [database.md](database.md); GAP-012, 017, 021, 030 |
| Experience and accessibility | Every exposed view/state has reviewed ownership, clear error/recovery and reachable actions; four styles and EN/FR/AR/RTL work across the declared device/browser matrix. | [ui.md](ui.md), [design.md](design.md), [extended_ui.md](extended_ui.md); GAP-025-026 |
| Release and service operation | Reproducible signed applications, safe upgrades, contracts, rollback, backups/restore, monitoring, paging, security response and capacity support the declared cohort. | [deployment.md](deployment.md), [testing.md](testing.md); GAP-001-003, 013-018, 033-036 |

Existing [explicit deferrals](gaps.md#8-explicit-deferrals--not-current-launch-blockers)
remain binding: no card/CMI processing, surge pricing, recurring bookings, passenger
driver selection or online-taxi map, unapproved pooling/intercity service, general
image upload, automated governance or automated multi-operator payouts. National
rollout is not required to release a full first-city service; isolation and a
repeatable per-city approval path are required before expansion.

## Non-negotiable constraints

- Retain FastAPI/PostGIS and shared Kotlin/Compose with native platform services;
  no framework migration or new architecture without an evidenced need and decision.
- Preserve Folded Streets, Street Press, Glazed Machine and grayscale/static
  Notepad. Style/language changes must not recreate auth or business coordinators.
- The backend owns identity, scope, eligibility, assignment, fares and money.
  Reconnect reads authority; uncertain business commands are not blindly replayed.
- Preserve the working alpha, original volumes, protected rollback records and
  unrelated dirty work. Never repeat the already applied staging credential cutover.
- The earlier Trial-only budget constraint remains until an explicit budget is
  approved. Prepare costed deployment options before any paid provisioning.
- Do not reuse synthetic approvals, users, secret material or permissive test
  configuration as production onboarding. Do not renew expired staff grants silently.
- Real participant enrollment, protected identity files, real transport/money and
  public activation require their applicable city/operator/owner acceptance gates.
  Ordinary authorized engineering, documentation and synthetic testing continue.

## Delivery sequence and bounded packets

The critical path is **R0 baseline -> R1/R2 decisions and reproducibility ->
R3-R9 production capability closure -> R10 device/staff acceptance -> R11 pilot
-> R12 public launch**. Code work may proceed when independent of a pending
external decision. One accountable function owns each packet; this plan does not
assume new staff, sub-agents or parallel chats have been authorized.

| Packet | Work and concrete output | Dependencies / mapped gates | Exit evidence |
| --- | --- | --- | --- |
| R0 Baseline and coverage | Reconcile actual Git roots/dirty changes, original requirements, domain source, current alpha manifests, all GAPs and test phases. Create a capability-to-source/test/UI/provider/evidence matrix and ranked defect list. Classify implemented, missing, locally verified, provider/device dependent and accepted separately. | First packet; all B/C packages | Every exposed capability above and GAP-001-037 is mapped, with file references, evidence freshness, owner and next action; no invented launch percentage. |
| R1 First-city launch contract | Prepare the scope/decision packet: city/operator, service area, licensed cohort, hours, tariffs/fees, cash/transfer/settlement responsibility, terms/privacy, support/on-call, budget, target devices/platforms, success/stop thresholds. Obtain the actual decisions and qualified reviews. | B-01; GAP-004, 010-011, 017, 024, 032 | Owner/operator-approved record and referenced reviews; production provider/hosting choices have explicit scope and cost authorization. Missing decisions remain named dependencies. |
| R2 Immutable engineering baseline | Preserve dirty work and alpha fallback; establish a reviewable source baseline and reproducible backend/web/Android/iOS artifacts, CI provenance, dependency/secret checks and contract compatibility. Repair real failures. | R0; GAP-001, 013-014, 016, 033-034, 036 | Exact source revision, artifact digests and passing appropriate immutable CI; signing ownership and release configuration verified. No broad staging/commit of unrelated work. |
| R3 Sustainable hosting and recovery | Design/provision the authorized isolated production/preproduction topology, private DB/worker/routing boundaries, least privilege, migration/release order, secret ownership, domains/TLS, storage growth/cost limits, backups/restore, rollback and teardown. Reuse existing architecture. | R1 budget/environment decisions; B-02; GAP-002-003, 015, 018 | Accepted environment inventory; measured migration/rollback and restoration to an isolated target; verified RPO/RTO against approved targets; no production dependence on an assumed free allowance. |
| R4 Real providers and event reliability | Accept map/search/routing licenses/endpoints/quotas, operational location policy, FCM/APNs and required identity/contact/crash/monitoring integrations. Exercise actual delivery, permission, timeout/quota and outage paths. | R1/R3 as applicable; B-04; GAP-006-009, 015, 023, 026, 028 | Provider/device acceptance per event and lifecycle state; honest narration/language fallbacks; approved secrets and budgets; failure behavior observed, not mocked acceptance. |
| R5 Full passenger and driver workflows | Repair missing on-demand and lifecycle behavior, restricted/onboarding states, no-supply/cancel/offer expiry, duplicate/concurrent/unknown-result handling, history/receipts and recovery. Verify server-authoritative effects through actual clients. | R0/R2; provider-dependent parts await R4; GAP-007, 018-019, 020, 025 | Both role journeys and meaningful negative/concurrency cases pass on named candidate/environment/device combinations; no SQL/manual API substitute for a missing client action. |
| R6 Routes and scheduled service | Close real route publishing, capacity/eligibility, booking, driver execution, commitments/deadlines, reminders, cancellation and no-driver/failure paths. Match the documented money model. | R1 scope/policy; R4-R5; B-03-B-06 | Populated passenger/driver/staff end-to-end cases plus deadline/conflict/recovery cases. Any pilot restriction is explicit and cannot count as full-release completion. |
| R7 Money and settlements | Implement/verify approved tariff, fee, cash, manual-transfer, review/dual-control, reconciliation, adjustment, dispute and driver settlement accounting. Validate all amounts and authorization boundaries. | R1 financial decisions; R2/R3; B-05; GAP-010, 024, 027 | Reconciled ledgers/receipts, meaningful double-submit/concurrent/unauthorized cases, correction and audit proof; approved controlled real-money exercise when permitted. No new card processor. |
| R8 Production staff, documents and participant protection | Close staff identity/MFA/grant lifecycle, independent approval, transitional-admin governance, protected file processing/access, communication/privacy, account rights, retention/holds, security incidents and staffed safety/support operations. | R1 responsible people; R3 secure stores; B-03/B-05; GAP-005, 011-012, 016-017, 020-023, 027, 029-031 | Actual trained/scoped staff, protected end-to-end cases, expired/revoked access denial, deletion/hold/audit proof, incident/support drills and independent security findings resolved. |
| R9 Every exposed page and supported platform | Reconcile all current views rather than treating the 213-view atlas as proof. Close incomplete/empty/error/denied states, navigation, populated forms, keyboard/insets, RTL, text scaling, focus and assistive behavior. Finish Android/iOS/web signing/distribution and compatibility. | R2 and relevant R4-R8 behavior; C-01; GAP-013-014, 025-026, 036 | Per-view/state coverage with actual artifacts; all critical journeys across four styles and EN/FR/AR using a documented risk-based device/browser matrix. Physical Android/iOS and screen-reader checks are explicit. No untested blanket cross-product claim. |
| R10 Hosted, device and staff acceptance | Execute applicable T0-T6 with immutable candidate. Verify long-session and restart recovery, background/lock/process death, network/provider loss, concurrency/load/capacity, paging, backup/restore, rollback and trained multi-role rehearsals. | R3-R9; B-02-B-05; GAP-014-019, 025, 028, 032-034 | Candidate-linked hosted/device/provider records, approved SLO/RPO/RTO/latency/capacity targets actually measured; no unresolved applicable release-blocking defect. Human/device access arranged before dependent tests. |
| R11 Authorized closed field pilot | Complete T7/T8 with approved participants, operating boundary, trained support, real licensed-driver onboarding and agreed money handling. Measure service, safety, reliability, costs and participant outcomes; run stop/rollback exercise and close defects. | R1, R10 and all applicable P0/P1 acceptance; B-06; GAP-019, 032 | Explicit owner/operator authorization before live transport; retained field evidence, outcome review and pilot exit decision. Synthetic rides do not close this packet. |
| R12 Guarded public release and handover | Close full-release scope and applicable P1/hardening requirements, independent review, stores, support, public terms, monitoring and sustainable economics; produce go/no-go dossier and guarded rollout/rollback. | Accepted R11; C-01-C-03; remaining applicable GAPs | Explicit public-launch decision, actual signed distribution and healthy guarded rollout, measured observation/incident response, accountable handover and per-city expansion controls. |

## R0: the first executable task

R0 is a bounded reconciliation, not an instruction to rebuild everything.

1. Verify repository roots and dirty state, then preserve/reference the existing
   candidate and latest accepted evidence. On 23 October, `git -C TaxiMobile
   rev-parse --show-toplevel` resolves to the workspace root; earlier memory
   describing a separate root must not override this observation.
2. Read the authoritative source/test paths for each capability and existing GAP.
   Reuse `backend/src/taximobile_api/domains/`, shared/native/web modules and
   `infra/scripts/` validators instead of scaffolding duplicate implementations.
3. Record gaps as concrete missing behavior or missing acceptance, with evidence
   date/candidate and exact next command/check. A stale report is not a new test.
4. Produce the first R1 decision packet and the smallest unblocked R2/R5 fix.
   Determine missing city/operator, budget/provider, signing/Mac/iOS and physical
   device inputs without blocking unrelated source work.
5. Exit after the coverage/decision/next-task artifacts are reviewable. Do not run
   hundreds of builds or another cosmetic variant to make the inventory complete.

Current checkpoint, 23 October: **R0 source/gap navigation baseline prepared;
R1 decision agenda prepared; R2 local candidate preserved; R2-R12 not launch-accepted.** The
[R0 baseline and ranked queue](launch/r0-baseline.md) maps 15 capability areas,
all 37 GAPs and candidate UI surfaces, with current local check provenance. It is
not assertion-level coverage or every-state runtime acceptance. The
[R1 decision packet](launch/r1-decisions.md) identifies the actual operating
decisions needed. The [R2 checkpoint](launch/r2-candidate.md) records an isolated
local commit, credential archive-scan fix and portable handoff correction, with
16 focused passing tests. The original checkout index/HEAD are preserved. Next
is candidate review and immutable remote CI; no unrelated dirty work may be staged.
No new production resource, provider purchase or participant activation is implied
by this checkpoint.

## Evidence and execution discipline

For each packet maintain a compact record with: packet and GAP/T IDs; named
owner/responsibility; dependency; exact source/artifact/config/environment identity;
scenario and expected result; actual result; commands/tests; privacy-safe artifact
references; limitations; acceptance authority/date; and next action. Link existing
governed acceptance records/templates rather than inventing parallel approval forms.

Use existing validators where applicable, including production environment,
managed PostGIS, pilot-city approval, maps/routing/navigation, monitoring,
operations identity, API contracts, source credentials, CI and test-phase evidence.
A valid template proves structure, not a provider/device/operational pass.

Each engineering slice follows: inspect -> bounded implementation -> meaningful
focused checks -> affected integration/device/provider evidence -> documentation
and checkpoint. Preserve failed observations and fixes. Run broad suites for
candidate integration or an evidenced risk; do not repeatedly rebuild unchanged
artifacts. Every newly observed regression gets a concrete failing case where useful.

Use the approved finite budgets for builds, test attempts and provider calls.
When an observer/harness fails, inspect the current app/server state before
retargeting; repair the observer separately from app behavior. Never repeat an
already admitted business command merely to obtain a cleaner recording.

At a continuation boundary, record the current slice, running process handles,
last confirmed state, artifact identity, checks remaining and next bounded action.
Finish an unblocked authorized slice before yielding; if an external dependency
blocks it, continue another useful slice. No recurring automation is created by
this goal. Pause only when the owner requests it; do not mark the entire goal
complete at a documentation, build, staging, T6 or synthetic-demo checkpoint.

## Owner and external decisions

Prepare concrete reviewable packets before requesting dependent authorization.
Track one table of pending inputs: requested decision, responsible person,
prepared artifact, affected packets, safe work that continues and resulting scope.
The first required decisions are first city/legal operator and service boundary;
hosting/provider spending ceiling; tariff/payment/settlement ownership; support
and incident owners; physical devices and signing/store access; and approved
pilot/SLO/stop thresholds. Do not invent names, licenses, budgets or launch dates.

Owner input on 23 October selects **Fès, union operation, member-only drivers and
ordinary passenger registration**. Android hardware and Google Play accounts are
available; connection, signing ownership and actual acceptance are still required.
Use **Fès Taxi Union** as the generic working name. The owner specifies autonomous
taxis and no separate union transport permit to obtain; keep individual driver,
vehicle and service checks distinct. Service boundary, verified roster ownership,
financial/support rules, applicable compliance records and iOS release resources
remain in the [R1 packet](launch/r1-decisions.md).
The [remote CI checkpoint](launch/r2-ci.md) records the draft source review,
observed failures and bounded corrections. The owner selected the existing
cooperative register for union membership. [The membership slice](launch/union-membership.md)
implements and locally verifies R5/R8 admission guards. The
[staff-register extension](launch/member-register.md) adds scoped audited web
administration, policy review and localized driver guidance. Its synthetic
rehearsal passed; terminal CI rejected web size. The
[session/release successor](launch/session-recovery.md) verifies expired-access
revocation and explicitly reviews the expanded web budget. Fresh immutable CI,
hosted upgrade and deployment acceptance remain open.
The [runtime-preserving migration fix](launch/runtime-preservation.md) closes a
source defect that could reset established credentials during normal deployment.
Focused unit and real local SCRAM checks pass; [CI 238](launch/runtime-preservation-ci-terminal-20261026.json)
now passes all eight required jobs and 1,458 backend cases. The actual guarded
TLS/schema rollout remains open and is stopped by the
[26 October Trial capacity read](launch/staging-capacity-stop-20261026.json).
The approved temporary S3 probe has
its own [provider evidence](launch/document-s3-provider-probe-20261025.json),
without accepting permanent document storage or the Trial scanner profile.

The earlier physical-Android deferral leaves hardware work pending. This new goal
includes preparing and obtaining that acceptance; it does not mean a device is
connected or that field participants have consented. Likewise, existing Railway
access is not permission to buy a plan, expand staff security privileges or
activate real transport. Honor the already authorized scope without repeatedly
asking for ordinary code, read-only or synthetic-test permission.

## Completion criteria

The goal is complete only when all of the following are true:

1. The capability matrix covers the full launch scope, and every enabled
   capability has accepted end-to-end and failure/recovery evidence on the actual
   signed/hosted release. Approved deferrals are unavailable and disclosed.
2. All applicable GAP-001-019 P0, public-release GAP-020-032 P1 and applicable
   GAP-033-037 hardening requirements are accepted by their real authorities.
   Required T0-T9 promotions have valid evidence; T10 is required before expansion.
3. Real Android/iOS device, provider, privacy, accessibility, security, account,
   staff, protected-document, money/settlement and service-operation checks pass
   within the declared scope. All unresolved blocking defects prevent promotion.
4. Restore/rollback and incident response are demonstrated, approved service and
   cost targets are measured, and funded accountable hosting/support exist.
5. The authorized field pilot meets its approved exit criteria; owner/operator
   and public go/no-go decisions precede actual guarded activation.
6. The public service is distributed, running and observed within approved limits,
   with a support/release runbook, secure credential ownership and rollback path.

Report engineering completion, operational readiness, pilot acceptance and public
launch separately. Do not average them into a readiness percentage or close this
goal because elapsed time, token use, a framework build or a board demo looks good.
