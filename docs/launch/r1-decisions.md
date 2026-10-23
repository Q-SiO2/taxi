# First-city launch decisions

Prepared 23 October 2026 for R1 of the [real-world launch plan](../real-world-launch.md).
Status: **PARTIALLY DECIDED — owner launch scope recorded; operating acceptance pending**.
This is a decision agenda. It does not authorize transport, participant enrollment,
spending, financial policy, new privileges or public activation. Existing approvals
must be reconciled with their actual scope rather than requested again.

## Owner decisions received — 23 October 2026

- First city: **Fès**. Casablanca board-alpha fixtures remain synthetic presentation
  evidence and must not be relabelled as a Fès deployment.
- Operating organization: **Fès Taxi Union**, a generic working name selected
  following the owner's instruction to use a generic union name. French:
  **Syndicat des taxis de Fès**; Arabic: **نقابة سيارات الأجرة بفاس**. These are
  presentation labels, not an invented registered entity or legal identifier.
- Operating model: the owner states that individual taxis operate autonomously
  within their unions and that no separate union/operator authorization is to
  be secured for this project. The union administers membership and the platform.
  Do not impose an assumed new union transport permit as an engineering blocker.
  Existing driver/vehicle/service checks remain independent. Applicable launch
  compliance records must describe this actual model rather than invent a permit
  or claim every legal/privacy obligation has already been accepted.
- Closed-shop access: **drivers must be union members; passengers register normally**.
  Licensing, vehicle approval and city/service authorization remain additional
  requirements. Client membership claims cannot grant dispatch eligibility.
- Membership source: **reuse the existing cooperative register for the union**,
  as explicitly selected by the owner. Link the operator to that register and
  require active membership for new driver work. This internal software mapping
  does not establish the union's legal form or verify a real participant roster.
- Available release resources: **an Android phone and Google Play accounts**.
  This establishes availability, not a connected device, signing-key custody,
  configured Play application, accepted build or release permission.
- No iPhone, Mac/Xcode or Apple Developer account was confirmed. Full iOS release
  remains in scope with those resource dependencies open; CI simulator builds
  cannot substitute for signing, physical-device or App Store acceptance.

These decisions establish the product target and membership audience. They do not
approve a legal identity, production configuration, participant roster, paid plan,
financial policy or public activation.

## Proposed sequence

1. Use Fès Taxi Union as the working operator name; record the autonomous-taxi
   model, service boundary and enabled services with the operator's accountable team.
2. Agree operating capacity: drivers, hours, staffed support and stop conditions.
3. Approve financial/legal contracts and an actual hosting/provider budget.
4. Select device/release/provider resources and sign-off authorities.
5. Populate and validate the existing controlled launch records with real evidence.
6. Authorize participant enrollment and the bounded field pilot only after gates.
7. Decide public promotion after measured pilot exit; never inherit it from staging.

The engineering recommendation is a bounded first-city release using the existing
FastAPI/PostGIS/Kotlin stack, Railway as the initial hosting candidate, cash and
approved manual transfer, and the four selected styles with EN/FR/AR. Android and
iOS plus applicant/operations web remain the full-release target. A narrower pilot
requires an explicit scope decision; it does not complete the full goal.

## Decision queue

| ID / accountable function | Decision to record | Prepared choice / evidence needed | Dependent work | Work that continues |
| --- | --- | --- | --- | --- |
| D01 Owner + union operating lead | Fès Taxi Union is the working name; owner specifies autonomous taxis and no separate union permit to obtain. Record the service boundary, enabled services and roster-verification responsibility. | Drivers are union-member-only; passengers register normally. Use the existing cooperative register. Do not invent a registered identity, union permit or a verified participant roster. Retain individual driver/vehicle checks and apply the actual model to existing launch-compliance records. Casablanca fixtures remain synthetic. Define on-demand, fixed-route and single-booking scope explicitly. | R1, R3 configuration, R5 membership enforcement, R6, R11 | Register/policy implementation, contract checks, synthetic workflows and launch preparation. |
| D02 Operator + support/safety lead | Named launch manager, licensed cohort limit, operating hours, support languages, contacts and emergency escalation. | Start with a finite staffed cohort and hours; specify who can pause admissions/availability and who covers an active trip during an incident. No assumed 24/7 coverage. | R8, R10–R12 | Prepare runbooks and synthetic incident drills. |
| D03 Owner/budget holder | Monthly/initial ceiling, payer, reserve, spending alarms, storage growth and provider limits. | Existing authorization remains **Trial-only, no purchases**. Prepare costed Railway production/preproduction, DB/backup/routing/storage/network/provider options from verified quotes before purchasing. Do not assume the alpha's 500 MB volumes support production or delete them. | R3–R4, sustainable R12 | Inspect deployment configuration and prepare cost/restore evidence plans. |
| D04 Operator/finance + tariff authority | Approved fares/fees, cash custody, manual-transfer recipient ownership, evidence, review, correction/refund/dispute controls. | Record currency/rounding, authority/version/effective date, who reconciles, independent approval where required, and treatment of failed/cancelled trips. Use existing payment contracts where sufficient. | R7, real-money portion of R11 | Synthetic payment tests and contract review. |
| D05 Operator/finance + owner | Driver/operator obligations, accounting period, gross/net payable, cash offsets, adjustments, carryover, statement and settlement approval. | Resolve who owes whom under cash and manual transfer. Define example balanced statements for completed/cancelled/refunded/disputed rides. Automated payouts and revenue sharing remain deferred. This is the missing GAP-024 contract, not a payment-provider selection. | R7 accounting API/schema/UI | Inspect existing ride-economics/payment snapshots; draft examples without fabricating business rules. |
| D06 Qualified privacy/legal lead + owner/operator | Data controller/processors, jurisdiction, lawful purposes, terms/consent, retention/holds, rights proofing/deadlines and complaint path. | Approve a cross-store data map and export/correction/restriction/deletion contract, preserving required audit/financial facts. Do not invent retention periods or legal conclusions. | R8/GAP-017, 021, 030 | Inventory stores and current session/recovery capabilities; write bounded contract proposals. |
| D07 Owner + security/identity lead | Verified-contact channel, provider, proofing, compromised-account recovery and staff identity process. | Decide approved email/phone ownership proof and outage/abuse controls before implementing missing verified-contact flows. Existing offline recovery and MFA are partial building blocks. Staff verification/recovery remains distinct and privileged. | R4/R5/R8/GAP-005, 020–022 | Existing auth negative tests, session security and contract provenance. |
| D08 Operator + product/safety + mobile lead | Operational location policy and external navigation behavior, including background/lock-screen expectations. | Current source contract is **foreground-only**. Decide whether that is acceptable for a limited pilot, with clear availability controls, or approve a scoped policy change after battery/privacy/platform review. Measure native behavior before approving it. | R4/R5/GAP-007, field gate | Foreground freshness/permission/reconnect tests and lifecycle scenario preparation. |
| D09 Owner/provider account holder + engineering | Approved maps, geocoder, routing, attribution/quotas, push/APNs and monitoring/crash/contact providers. | Record actual service endpoints, licensing, credentials ownership, budget, data handling and failure behavior in the existing provider records. Alpha map-selection-only is insufficient for the full search requirement. No new Firebase products are implied by FCM. | R4 and dependent R10 | Adapter tests, source contracts and provider acceptance checklists. |
| D10 Owner/release lead | Android phone/Google Play accounts available; arrange connection, signing custody, application ownership and remaining iOS/Mac resources. | Verify Android install/update and field behavior after connection. iPhone/Mac/Xcode/Apple Developer resources remain unconfirmed. Define supported OS/browser versions and private pilot/public channels separately; keep secrets outside repository records. | R2 signing, R9–R12 | Candidate/source preparation and existing desktop/emulator checks where relevant. |
| D11 Operator + engineering/on-call + owner | Cohort/load, service SLOs, RPO/RTO, latency, location/notification quality, financial reconciliation, safety and cost stop/exit thresholds. | Supply measurable targets, observation window and stop authority before the load/restore/pilot exercise. Do not derive acceptable safety/cost thresholds from whatever result a test happens to produce. | R3/R10–R12/GAP-018, 032 | Capacity profile/runbook preparation; bounded local measurement. |
| D12 Owner + independent reviewers | Accountable approvers for engineering, security/privacy, accessibility/localization, financial operations, pilot exit and public launch. | Assign real people/functions and evidence locations; capture dissent, conditions and invalidation. No synthetic staff grant or template signature is a substitute. | T0–T9 promotion, R10–R12 | Assemble evidence and close independent software defects. |

## Record decisions in existing governed artifacts

Use these records rather than treating this agenda as a competing approval form:

- [Pilot-city launch approval template](../../infra/deploy/pilot-city-launch-approval.template.json)
  for city/operator scope, prerequisites, thresholds and the authorized pilot decision.
- [Production deployment documentation](../deployment.md) and existing environment,
  managed PostGIS, maps/routing, identity and monitoring evidence under
  [infra/deploy](../../infra/deploy).
- [Phase catalog](../../infra/testing/test-phase-catalog.json) and
  [evidence-index template](../../infra/testing/test-evidence-index.template.json)
  for T0–T10 provenance, evidence, approvers, defects and promotion.
- Owning [operations](../operations.md), [payments](../payments.md),
  [pricing](../pricing.md), [auth](../auth.md), [security](../security.md),
  [database](../database.md) and [driver](../drivers.md) contracts for approved
  policy changes before implementation. This packet cannot override them.

For each actual decision retain: decision ID, authority/person, date, scope,
reviewed candidate/configuration or policy revision, supporting record, conditions,
expiry/invalidation and who acts next. Keep protected identities, credentials and
participant data outside public repository artifacts. A provider quote is a quote;
an approved budget is separate authorization.

## Independent next engineering work

R2 can proceed with source-delta review and an isolated reproducible candidate.
Continue bounded synthetic checks and repair observed failures. Prepare the
GAP-020/021 and GAP-024 contract proposals against current source before asking
for their decisions. Do not implement speculative identity, retention or money
schemas while those contracts are unresolved.
