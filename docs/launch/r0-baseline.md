# R0 launch baseline — 23 October 2026

This is the first bounded source/evidence reconciliation for the [real-world launch goal](../real-world-launch.md). It preserves the board alpha and identifies work for pilot/public launch. It does not accept a live service.

## Fresh local evidence

- Git root `C:/Users/Q/Projects`; branch `codex/gap-001-release-baseline`; HEAD `2835c8aa7f5e97a17afcdbe647fe589cbd0421e1` with substantial pre-existing dirty work preserved.
- Backend unit suite: **983 passed**, exit 0. No API/integration, hosted, provider or device suite was run for this baseline.
- Mobile API contract: **84 HTTP calls + 1 WebSocket**; operations web: **112 HTTP calls**. Both local validators passed.
- Generated source inventory: **245 backend HTTP operations, 52 migrations, 9 administrative roles**. The inventory is a source contract, not an accepted product surface.
- CI-definition security gate and source credential hygiene gate passed locally. This is not a vulnerability audit or immutable remote CI run.
- File manifest is a later allowlisted metadata snapshot, not a source archive or proof that the tested dirty tree was frozen. Source bytes, signing and immutable candidate CI remain R2 work.

See [baseline/check provenance](r0-baseline-20261023.json), [generated contracts](r0-source-contracts-20261023.json), [capability/GAP/test navigation index](r0-coverage-20261023.json) and [surface navigation index](r0-surface-index-20261023.json). Test filename matches support navigation only; they do not prove assertion-level coverage. Acceptance is **not established by this R0 review**, which does not assert that protected approvals are absent elsewhere.

## Capability map

| Capability | Source assessment | Packet | Next action |
| --- | --- | --- | --- |
| Identity and accounts | PARTIAL | R5/R8 | Account lifecycle and verified-contact recovery remain partial; agree proofing, retention and rights policy before implementing their missing contracts. |
| Passenger on-demand | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R5 | Run candidate-bound client journeys and negative/concurrent recovery cases; retain alpha trips as historical synthetic evidence. |
| Licensed-driver lifecycle | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R5/R8 | Exercise protected application, correction, eligibility, vehicle and live-driver lifecycle using approved synthetic fixtures before enrolling actual drivers. |
| Fixed routes | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R6 | Rehearse publish, browse/book, capacity, cancellation and execution under the approved operator service scope. |
| Scheduled bookings | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R6 | Rehearse commitment/deadline/conflict/no-driver and cancellation paths through all three role clients. |
| Maps, search and navigation | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R4 | Select licensed production providers, quotas and attribution; validate service boundary and EN/FR/AR guidance/fallback on devices. Map selection alone remains an alpha restriction. |
| Location and lifecycle | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R4/R5 | Keep documented foreground-only policy until an explicit operational decision; measure background/lock/navigation/process-death behavior and safe availability with actual devices. |
| Communication and notifications | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R4 | Accept real FCM/APNs and participant coordination per event/state with acknowledgement, privacy and fallback; mocks are insufficient. |
| Cash and manual transfer | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R7 | Agree tariff/fee and cash/transfer responsibilities, then reconcile controlled synthetic transactions before any specifically approved real-money exercise. |
| Driver settlement | PARTIAL | R7 | Implement the currently missing operator-to-driver accounting only after obligations, period, cash offset, adjustments and approval authority are agreed; passenger payment settlement is a different record. |
| Safety and support | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R8 | Name staffed responders and service hours, contact/escalation ownership and emergency limitations; rehearse triage, paging, handover and closure. |
| National/city operations | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R1/R8 | Configure approved city/operator data and least privilege; exercise independent approvals and tenant isolation without renewing expired synthetic grants. |
| Protected information | PARTIAL | R8 | Complete approved data map and rights workflows across database, files, logs and backups, respecting holds and required financial/audit retention. |
| Experience and accessibility | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R9 | Review every indexed surface/state on the actual device/browser matrix, four styles and three languages; include assistive technology and text scaling. |
| Release and service operation | SOURCE_PATHS_PRESENT_NOT_FULLY_ACCEPTED | R2/R3/R10 | Bind exact source, signed artifacts and configuration to immutable CI, then verify restore, rollout, contracts, alerting and approved capacity targets. |

## GAP work queue

Every GAP retains its authority and priority in [gaps.md](../gaps.md). No gate is closed by this index. Exact source, test-navigation and existing validator paths are in the JSON matrix. Responsible functions are assigned below; named accountable people remain an R1 decision.

| GAP | Priority / packet | Work classification | Next action |
| --- | --- | --- | --- |
| [GAP-001](../gaps.md) | P0 / R2 | SOURCE_BASELINE | Preserve reviewed work in an isolated candidate; do not stage unrelated dirty changes. Obtain passing immutable CI and artifact provenance. |
| [GAP-002](../gaps.md) | P0 / R3 | ENVIRONMENT_ACCEPTANCE | Prepare isolated production/preproduction inventory and costed topology; staging success is not production acceptance. |
| [GAP-003](../gaps.md) | P0 / R3 | RESTORE_ACCEPTANCE | Measure backup and restore to an isolated target with approved retention, RPO/RTO and growth limits. |
| [GAP-004](../gaps.md) | P0 / R1 | OWNER_OPERATOR_DECISION | Obtain actual city/operator/service boundary, participant and allowed-service decisions. |
| [GAP-005](../gaps.md) | P0 / R8 | IDENTITY_GOVERNANCE | Name staff and joiner/mover/leaver, MFA, recertification and break-glass authorities; test least privilege. |
| [GAP-006](../gaps.md) | P0 / R4 | PROVIDER_DEVICE_ACCEPTANCE | Accept map/routing provider licenses, endpoints, limits, attribution and field behavior. |
| [GAP-007](../gaps.md) | P0 / R4/R5 | LOCATION_POLICY_AND_DEVICE | Resolve foreground-only operational suitability explicitly; test lock/background/navigation, denial, stale fixes and process death. |
| [GAP-008](../gaps.md) | P0 / R4 | PROVIDER_ACCEPTANCE | Approve production place discovery provider, service-area bounds, privacy and outage behavior; do not count alpha map-only selection as full search. |
| [GAP-009](../gaps.md) | P0 / R4 | PUSH_PROVIDER_DEVICE | Verify Android/iOS token lifecycle, permissions, actual delivery and per-event fallback using authorized provider projects. |
| [GAP-010](../gaps.md) | P0 / R7 | FINANCIAL_ACCEPTANCE | Approve tariffs, fee/cash/transfer custody and dual control; prove reconciliation then authorized real-money handling. |
| [GAP-011](../gaps.md) | P0 / R8 | STAFFED_OPERATIONS | Assign real support/safety hours, contact/escalation and paging ownership; rehearse incidents. |
| [GAP-012](../gaps.md) | P0 / R8 | PROTECTED_STORE_ACCEPTANCE | Accept document store, scanning/quarantine/access and lifecycle/retention with synthetic protected fixtures before real documents. |
| [GAP-013](../gaps.md) | P0 / R2/R10 | SIGNING_AND_DEVICES | Obtain signing/store ownership and macOS/iOS resources; produce exact signed artifacts and test install/update on real phones. |
| [GAP-014](../gaps.md) | P0 / R2/R9 | BROWSER_ACCEPTANCE | Run authenticated applicant/operations browser E2E against the exact hosted candidate and review security/cache behavior. |
| [GAP-015](../gaps.md) | P0 / R3/R10 | ON_CALL_ACCEPTANCE | Connect actual telemetry, crashes, paging and accountable rota; observe firing and recovery. |
| [GAP-016](../gaps.md) | P0 / R2/R10 | INDEPENDENT_SECURITY | Retain scan/SBOM/provenance evidence and obtain qualified independent security review with tracked findings. |
| [GAP-017](../gaps.md) | P0 / R1/R8 | LEGAL_PRIVACY_DECISION | Obtain qualified transport/privacy/terms review and approved data map; do not fabricate legal acceptance. |
| [GAP-018](../gaps.md) | P0 / R3/R10 | MEASURED_CAPACITY | Approve finite cohort/targets, measure capacity, failure/recovery and cost on authorized production-like resources. |
| [GAP-019](../gaps.md) | P0 / R10/R11 | FIELD_ACCEPTANCE | Complete authorized whole-city rehearsals, rollback and actual participant pilot evidence after gates. |
| [GAP-020](../gaps.md) | P1 / R5/R8 | MISSING_VERIFIED_CONTACT_WORKFLOW | Choose ownership verification/delivery/proofing and compromised-account recovery policy, then implement missing workflow and negatives. |
| [GAP-021](../gaps.md) | P1 / R8 | MISSING_RIGHTS_WORKFLOW | Agree data map, retention/hold rules, deadlines and proofing; implement export/correction/restriction/deletion safeguards and audited operator actions. |
| [GAP-022](../gaps.md) | P1 / R8 | SCOPED_GRANTS_ACCEPTANCE | Verify implemented grant maker/checker and actual staff lifecycle; decide any additional sensitive-command dual control in owning policy. |
| [GAP-023](../gaps.md) | P1 / R4/R8 | COORDINATION_ACCEPTANCE | Accept implemented private coordination and safe contact policy with field participants and fallback. |
| [GAP-024](../gaps.md) | P1 / R7 | MISSING_DRIVER_ACCOUNTING | Approve driver/operator obligations, payable periods, cash offsets, adjustments, statements and controls before designing accounting schema/API. |
| [GAP-025](../gaps.md) | P1 / R9 | ACCESSIBILITY_LOCALIZATION | Execute full surface/state/style/language and TalkBack/VoiceOver/keyboard/text-scaling acceptance; obtain translation review. |
| [GAP-026](../gaps.md) | P1 / R4/R9 | NARRATION_COPY_ACCEPTANCE | Review actual narration and operational copy in EN/FR/AR, including explicit unsupported-language/provider fallback. |
| [GAP-027](../gaps.md) | P1 / R7/R8 | ABUSE_PROGRAM | Set proportionate approved abuse rules, investigations and audit using existing controls; avoid speculative automated profiling. |
| [GAP-028](../gaps.md) | P1 / R4 | EVENT_RELIABILITY | Validate each critical event expiry/deduplication, acknowledgement, escalation and outage fallback on real clients. |
| [GAP-029](../gaps.md) | P1 / R8 | ADMIN_GOVERNANCE | Prove transitional admin is absent or explicitly constrained with real operator governance and audited exceptions. |
| [GAP-030](../gaps.md) | P1 / R8 | CROSS_STORE_RETENTION | Exercise holds, purge/erasure and backup expiry across every actual store and record evidence. |
| [GAP-031](../gaps.md) | P1 / R8/R10 | INCIDENT_ACCEPTANCE | Exercise security incident declaration, restriction, escalation, evidence preservation, recovery and independent review. |
| [GAP-032](../gaps.md) | P1 / R1/R11 | THRESHOLD_DECISION | Approve availability/latency/safety/notification/cost, stop/exit and expansion thresholds before measurement-based go/no-go. |
| [GAP-033](../gaps.md) | P2 / R2 | CI_HARDENING | Establish exact current candidate CI, ecosystem scans, coverage expectations, signed provenance and all shipped targets. |
| [GAP-034](../gaps.md) | P2 / R2 | CONTRACT_DRIFT | Preserve generated current OpenAPI/migration/permission inventory and contract checks; evaluate payload schema drift separately. |
| [GAP-035](../gaps.md) | P2 / R10 | ISOLATION_ACCEPTANCE | Exercise cross-city/operator reads, commands, live events, files and analytics with negative cases; T10 before expansion. |
| [GAP-036](../gaps.md) | P2 / R2/R10 | RELEASE_LIFECYCLE | Approve platform/version support and owners, then test signed compatible/obsolete upgrades, cache propagation, rollback and continuity. |
| [GAP-037](../gaps.md) | P2 / R8/R10 | ANALYTICS_GOVERNANCE | Reconcile event totals, duplicates/late arrivals, definition revisions, small-cell suppression, ownership and audit changes. |

## Phase acceptance reconciliation

All eleven phases T0–T10 are indexed in the [phase requirements map](r0-phase-index-20261023.json). Required evidence, predecessor and approver functions come from the existing phase catalog. Their actual accepted records have not been reconciled by this source review; an unfilled template does not erase historical engineering evidence or create production acceptance. Use the existing validator with the actual controlled evidence record and `--require-through` for the intended promotion.

## Ranked next work

1. **R2: preserve a reviewable engineering candidate.** The checkout is dirty and historical CI belongs to older commits. Compare against the retained alpha manifests, separate intentional source deltas, and prepare an isolated candidate without staging unrelated work. Run relevant checks once against that candidate before immutable CI.
2. **R1: resolve first-city operating decisions.** Use the [prepared decision packet](r1-decisions.md). City/operator authorization, budget, provider accounts, financial responsibility and real staff cannot be manufactured in code.
3. **R8/GAP-020–021: verified contact and rights workflows.** Existing offline recovery, sessions and password controls are partial coverage. No complete export/correction/restriction/deletion workflow was found in the reviewed auth API. Agree retention/hold, verification and fulfillment policy before a bounded API/schema implementation.
4. **R7/GAP-024: driver accounting.** Existing earnings and passenger payment/refund/transfer settlement references do not establish driver payables, settlement periods, offsets or adjustments. Obtain the financial contract before implementing it.
5. **R4/R9/R10: provider and hardware acceptance.** Preserve foreground-only policy pending decision. Arrange real Android/iOS, Mac/signing and providers, and expand source surface candidates into actual state-by-state acceptance.

## First bounded correction and handoff

The current contract baseline is now explicitly dated at 245 backend operations and 84 mobile calls. Older 244/83 counts in historical evidence remain historical; they must not be relabelled as current production proof. No application defect was established by the passing checks, so this packet does not invent a backend change or schema.

R0 source navigation/queue and the R1 decision packet are prepared. Detailed assertion-level and every-state runtime verification remain in the execution packets. No paid provisioning, role expansion, credential cutover, participant enrollment, real-money operation or production activation occurred. All commands in this packet have finished; no test process is left running.

Next bounded task: inspect the reviewed source delta against the existing alpha manifests and prepare the R2 isolation/commit plan, keeping unrelated dirty work intact. Obtain owner decisions from R1 as concrete dependent work becomes ready.
