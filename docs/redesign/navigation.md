# Navigation and integration plan

**Proposed; owner approval pending.** IDs describe reviewable design surfaces,
not new backend resources or necessarily separate navigation routes. Split the
current large composables into task views after approval, retaining coordinators,
session lifetime, domain state and existing gateway contracts. Navigation carries
only safe resource/context identifiers; protected data is loaded under the
current authorized session and scope.

## Shared authentication and account security

S00 restores into the actual AppUiState: compatibility S01, welcome S02,
authentication S03–S07, application gating D00/D06, or current role journey.
Sign-in never forces a restored active ride to idle home. S08 clears revoked or
expired identity and returns to S03; S09 overlays last-confirmed permitted work.
Native rationale S10/S11 returns to its initiating context, not a fabricated OS
permission result. S12 returns to the account/welcome caller. S13 clears local
session state using the existing fencing contract.

Account → S14 security hub → S15 password / S16 sessions / S18 code generation.
S16 → S17 exact-session revocation review → refreshed S16; revoking current
session returns to signed-out state. S18 → S19 only after the actual server
bundle; acknowledgement clears the one-time display and returns to S14.
Password changes/recovery use the actual credential-clearing outcome; no command
is replayed after authentication or MFA.

## Passenger

Ride R00 → destination R01 → point summary R03 → pickup R02 → R05 review.
R38 recent destinations and R41 city choice return to this draft. A point/city
change invalidates the old quote. R42 is development-only and absent from the
presentation/release navigation. R04 provider lookup is gated outside the map-only
alpha; it must never become a dead search launcher.

R05 → R06 fare detail / R07 payment choice → R05. Request enters R08; the actual
read result selects R09 matching, R10 unmatched or R11 assigned. Server phase
selects R12 approaching, R13 arrived, R14 in ride and R17 completed/cash pending.
Back/dismiss does not cancel. R15 is an explicit cancellation review; confirmed
cancellation selects R16, while a conflict reloads the actual active phase.

Assigned journey → R36 safety / R37 bounded coordination; return restores the
same authoritative journey. R17 → R18 receipt → R21 rating when supported.
Payment method/capability and actual payment state select R19 instructions and
R20 processing/refund detail. A submitted transfer claim does not settle money.
R22 trip list → R23 selected history → R18 receipt as permitted; Back preserves
the list position and filters.

R24 fixed-route directory → R25 exact direction → supported point/review flow.
R26 schedule selection → R27 quote/terms review → R28 upcoming list → R29 exact
booking detail/cancellation. A commitment is not an active ride until the real
handoff; no local countdown advances it.

R30 account → R31 profile / R32 inbox / R33 help / S14 security / S12 locale.
R33 → R34 support creation or R35 own case; safety has separate R39 history and
R40 composer. Notification navigation loads only the authorized resource and
handles missing/restricted records safely. Case participants see the actual
public response, not operations notes or an invented chat history.

## Driver

D00 application overview → D01 city/application → D02 answers/credentials →
D03 evidence → D04 vehicle → D05 review → D06 actual status. Additional-information
state reopens only editable evidence under the actual requirement version.
D07 explains authorization restrictions; account creation is not eligibility.

D10 offline Work → D38 city/service choice → D11 readiness diagnostics where
needed → confirmed D12 online. Private offer type selects D13 immediate,
D14 scheduled or D41 immediate fixed route. Offer expiry/conflict/uncertain
acceptance selects D15 and refreshes; it never restarts the response window.
Confirmed assignment enters D16 pickup navigation → D17 at pickup → D18 trip →
D19 completion review → D20 cash confirmation. Only actual phase allows each
command. D21 pending cash → D22 exact settlement review remains independently
recoverable after completed trips and process restarts. D23 earnings / D24 detail /
D25 work history display recorded facts.

D26 upcoming commitments → D27 exact detail/handoff; D34 preference controls
future scheduled offers separately from present availability. D28 account →
D29 vehicles → D30 registration/detail → D37 deactivation review, plus D35
read-only cooperative membership, D36 credentials, D31 inbox, D32 support,
D33 assigned safety/coordination, D39 safety history and D40 report creation.
S14–S19 security and S12 locale are shared. Returning from a secondary view
restores current offer/job state without submitting a command.

## Applicant

A00 welcome → A01 sign-in / A02 registration → A03 city/application list.
A04 overview → A05 answers → A06 evidence → A07 vehicle → A08 exact review →
A09 server status/timeline. A10 additional information reopens allowed fields;
A11 withdrawal is separate explicit review. A12 account/locale/sign-out returns
to the public shell. Protected-document upload/retrieval remains capability-gated;
the portal cannot pretend a supplied file was accepted or reviewed.

## Operations

O00 → O01 MFA (O70 saved recovery-code mode) → O03 authorized scope → workspace.
O04 handles loading/session/access failures. O02 recent-MFA step-up returns to
the reviewed record and requires explicit submission; no automatic replay.
Changing market/operator/city clears incompatible selection, confidential detail
and obsolete reads before loading the new scope.

| Workspace family | List / detail / editor / reviewed action path |
| --- | --- |
| Cities/control plane | O05 overview → O06 cities → O86 selected city → O07 identity creation, O08 area versions → O67 boundary editor → O09 review; O10 configuration → O11 review/activation; O12 readiness → O87 decision; O13 lifecycle; O14 operators → O15 creation / O16 lifecycle / O66 service assignment |
| Pricing | O17 tariffs → O18 editor → O79 lifecycle; O19 fees → O20 editor → O80 lifecycle; O21 scheduling → O22 editor → O81 lifecycle. Save draft and activate version are separate commands. |
| Published routes | O23 catalogue → O24 identity / O25 directional version → O26 publication, O82 replacement or O83 retirement. No inferred reverse route. |
| Staff | O27 grants/requests → O28 request / O29 revocation request → O30 independent decision. Creating a request does not immediately grant/revoke authority. |
| Recruitment | O31 queue → O34 application → O36 permitted protected document / O35 decision; O32 requirements → O33 full item editor → O78 lifecycle. O62 city authorization → O63 suspend / O64 revoke / O65 reinstate. |
| Payments | O37 overview → O38 recipients → O76 creation → O68 verify/retire; O39 capability versions → O77 creation → O69 submit/approve/activate; O40 transfer queue → O41 independent statement-based decision; O42 confirmed-refund evidence → O43 immutable ledger. |
| Scheduling/intelligence | O44 actual exceptions; O45 aggregate overview → O46 report detail; suppressed cells and missing data remain explicit. |
| Support/safety | O47 scoped queues → O48 support detail → O84 claim/acknowledge, O49 transition or O50 restricted handoff; O71 safety detail → O85 transition. O75 overdue alert → O51 delivery acknowledgement. O52 retention → O72 record detail → O73 hold / O74 release. |
| Security/audit | O53 exact authorized-case target → O54 containment review; O55 incident queue/create → O56 responsibility → O57 immutable event → O58 lifecycle → O59 postmortem. O60 audit is read-only; O61 distinguishes empty/restricted/failed detail. |

Reviewed dialogs return to the exact parent record on cancellation. Confirmed
writes refresh the actual affected record/list; conflicts require fresh review.
Preserve safe list filters/scroll when navigating Back; do not retain confidential
detail across scope/session changes. Unknown write outcome remains pending until
reconciled. Root navigation cannot bypass role checks or expose a private record.

## Deferred capabilities

L00–L08 are complete design outlines for possible later capabilities, with an
explicit missing-contract explanation and no active alpha destination. Approving
the visual plan does not approve OTP, card/wallet/payout providers, saved-place
persistence, continuous sharing, account export/deletion, general communication,
emergency integration, service categories or cooperative governance business rules.
Their actual delivery still follows B/C product/provider/security acceptance.

The [wave ledger](wave-assignment.md) assigns every view once. Each [individual
specification](coverage.md) carries controls, authority, states and acceptance;
the [atlas](page-atlas.html) makes every composition reviewable before execution.
