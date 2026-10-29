# Applicant and operations page book

**Proposed — owner confirmation precedes implementation.** Retain the existing
Compose web module and its separate applicant/operations composition roots.
The new identity applies throughout; web density and navigation are purpose-built.
Component IDs are in [components.md](components.md); global tokens are in
[visual-system.md](visual-system.md). IDs describe pages, detail views and review
dialogs. A new design ID does not imply a new backend endpoint or browser route.

## Common web contract

Applicant: friendly single-column task pages with a 560 px content maximum,
640–720 px review where needed; desktop welcome may have one illustration column.
No operations sidebar. On narrow screens illustration moves below useful content.
Documents and identity inputs never become decoration or proof of verification.

Operations: 232 px labelled sidebar in the selected identity, 64 px persistent
scope/header, neutral main workspace, table/master list + detail panel, stable
review footer. Group navigation by **Service setup**, **People**, **Money**,
**Operations**, **Security**. The 14 existing destinations remain permission-gated;
grouping does not grant a new permission. Scope is visible in header, detail and
action review. No enormous empty KPI tiles or dashboard rainbow.

| Profile | Applies to every relevant surface |
| --- | --- |
| G | EN/FR/AR, 360/768/1024/1440 px and 200% zoom, keyboard-only, focus order, RTL, reduced motion, no body text below proposed scale |
| F | Default/invalid/busy/conflict/rate-limit/offline/uncertain outcome; persistent labels, safe draft, one write, error summary and first-invalid-field focus |
| Q | Loading/empty/filtered-zero/error/stale/suppressed/restricted, authentic pagination, stable selection; failed query is not zero results |
| A | Active market/operator/city scope, live permissions, recent MFA, independent-review requirements, optimistic versions, no cross-scope stale detail |
| P | Confidential document/participant/case/payment facts minimized, no unnecessary preview or raw payload, authorized no-store retrieval |

G always applies. The final column adds specific checks; profiles carry the
full state/variant set. All fields/options come from existing typed forms/API
records. No arbitrary JSON editor or user-entered identifiers as authority.

## Applicant portal

Source: `applicant/ui/ApplicantPortalApp.kt`, `ApplicantApplicationEditor.kt`,
`ApplicantComponents.kt`, `ApplicantPortalCoordinator.kt` and document picker.

| ID / page | Composition and visual choices | Fields/options / genuine actions | Profiles / acceptance |
| --- | --- | --- | --- |
| A00 Welcome | Role-clear introduction, compact city/taxi artwork, readable language entry and sign-in/create buttons | Sign in/Create account; basic requirements and permitted city catalogue | Q; no dispatch access promise; no operations identity/navigation |
| A01 Sign in | Shared identity/password form, focused card in neutral page | Email/phone + password, reveal, real supported recovery navigation | F; auth failure/throttle/offline; applicant role boundaries retained |
| A02 Registration | Single-column supported contact/name/password fields with inline help | Create account; Back; confirmation then sign-in as actual auth contract | F; no OTP/contact-verified badge; source/API behavior governs acknowledgement |
| A03 City/application list | City labels and short requirements; existing own applications separate | Select permitted city; open/start own application; refresh | Q/F; unknown catalogue not empty; unsupported city not selectable |
| A04 Application overview | Requirement checklist, state/timeline and current next step; no sprawling editor at once | Open Identity/Documents/Vehicle; permitted draft save/submit | Q/F; current server version and requirement set explicit |
| A05 Identity/credential step | Requirement-driven labelled fields, descriptions as optional accordions | Enter only actual required values; Save/Continue; Back | F/P; no sensitive values in error or URL; no fake document credential approval |
| A06 Evidence/document step | C29 slots, metadata/status, concise permitted-type/limit instructions | Pick/upload/replace/delete permitted PDF/JPEG/PNG; retry rejected operation | F/P; capability missing explains pending secure storage; scanning state not success |
| A07 Vehicle step | Make/model/color/taxi identifier and actual required type/capacity in small groups | Save supported vehicle draft; inspect validation; Back | F; create record does not verify vehicle or authorize service |
| A08 Review/submit | Readable sections with Edit links, missing requirements, exact city/services | Submit once; return to edit; permitted withdrawal separate review | F/P; optimistic version conflict reloads safely; no premature success timeline |
| A09 Status/timeline | Current state prominent, compact static timeline, safe review explanation | Provide requested information; permitted withdraw; refresh | Q/F/P; no fabricated completion percentage or review deadline |
| A10 More information/replacement | Requested items isolated; previously submitted facts read-only except allowed fields | Replace permitted evidence; resubmit actual action; Back | F/P; no silent rewriting of accepted evidence |
| A11 Withdrawal review | Target application/city and consequences in C22 | Withdraw/Keep application | F/P; no closure from dismissing dialog; conflict handles live status |
| A12 Account/language/style/sign out | Supported local language and four-style settings, role label, no financial dashboard | Language; Style; Sign out; approved recovery/security links | F/Q; no fake deletion/export/contact editing |

## Protected authentication and shell

Source: `operations/ui/OperationsApp.kt`, `OperationsComponents.kt`,
`operations/model/OperationsModels.kt`, `OperationsCoordinator.kt`.

| ID / page | Composition and visual choices | Options / genuine actions | Profiles / acceptance |
| --- | --- | --- | --- |
| O00 Sign in | Narrow identity/password card; discreet TaxiMobile Operations header; neutral brand side panel desktop only | Existing admin identifier/password; reveal; Sign in | F/A; no role picker claiming rights; credentials not in route/local storage |
| O01 MFA verification | Focused code field, clear challenge context, recovery-code secondary mode | Submit actual TOTP; use saved recovery code; Back/cancel as supported | F/A; preserve response semantics; no unsupported SMS MFA; no code persistence |
| O02 Step-up review | Small MFA dialog showing pending action/scope separately from verification | Verify; then explicitly review and click action again; Cancel | F/A; verification never auto-replays the dangerous command |
| O03 Scope picker | Labelled market → operator → city hierarchy with loaded records and current scope | Choose allowed record; refresh; narrow menu alternative | Q/A; scope change cancels old reads and clears protected detail/drafts with warning if dirty |
| O04 Access/session gate | Clear permission/expired-session explanation; no protected data remnants | Sign in again; choose permitted destination; refresh authority | Q/A/P; hidden navigation is not authorization; revoked permissions clear cached sensitive detail |

## Service setup and configuration

Source: `OperationsScreens.kt`, `ControlPlaneEditors.kt`,
`CityAuthorizationReview.kt`, `FixedRoutesScreen.kt`,
`PricingEconomicsScreen.kt`, `PricingEconomicsEditors.kt`.

| ID / page | Composition and visual choices | Options / genuine actions | Profiles / acceptance |
| --- | --- | --- | --- |
| O05 Rollout overview | Compact scope summary, city state table, readiness rows with evidence freshness; chart only if useful | Open city/readiness; refresh; filter supported status | Q/A; no global green-ready percentage inferred from source/tests |
| O06 Cities | Label/status rows and selected city summary; lifecycle and config separated | Select/Create city; inspect current/draft config; readiness | Q/A; explicit draft/configuring/pilot/active/paused/retired labels |
| O07 City creation | Small full-page/drawer form with meaningful label/code/market fields from existing contract | Validate; Create; Cancel | F/A; no city activation side effect |
| O08 Service-area versions | Version list, static geometry preview and bounded coordinate table with label/status | Create/edit permitted version; inspect geometry; submit for review | F/Q/A; no arbitrary JSON or service-area ownership inference |
| O09 Service-area review | Version diff/geometry, accountable owner/reviewer facts, consequence summary | Approve/reject permitted version; reason and recent MFA as required | F/A; maker cannot approve own record; conflicts refresh |
| O10 Configuration assembly | Sections choose compatible loaded tariff/fee/schedule/payment/requirements/routes; missing prerequisite checklist | Assemble/update draft; inspect record details; submit review | F/Q/A; same city/operator/service and version compatibility enforced server-side |
| O11 Configuration review/activation | Before/after version summary, effective date, affected services and readiness | Approve/reject; activate only actual allowed command after separate review | F/A; independent reviewer preserved; source UI does not satisfy lifecycle authority |
| O12 Readiness evidence | Three clear groups: pilot entry/public activation/post-launch; each criterion state/owner/reference/date | Record only actual supported passed/failed decision with safe reference | F/Q/A/P; no copied legal/private evidence file; expired evidence clearly marked |
| O13 City lifecycle review | Current/target state and required evidence side by side, warning for pause/retire | Confirm permitted transition after explicit owner/reviewer/MFA flow | F/A; phase gates/independence intact; no status toggle optimism |
| O14 Operators | Label/status list with services/cities and selected details; assignments separated from status | Create operator; inspect/change allowed status; service assignment | Q/A; scope persists; no operator-selected self-authority |
| O15 Operator creation/edit | Labelled existing identity fields, current scope, concise validation | Create/update permitted fields; Cancel | F/A; no guessed bank/payment details or privilege edits |
| O16 Operator status/assignment review | Explicit target, service/city links and proposed status with consequence | Confirm allowed status/assignment; separate actions | F/A; no combined hidden side effects; optimistic conflicts readable |
| O17 Tariffs | Version table with service, effective dates and status; total/rules in detail | Create permitted tariff; inspect/review/activate through existing lifecycle | Q/A; prices not inferred from client calculations |
| O18 Tariff editor/review | Typed component fields with units, effective dates, current vs draft summary | Save/submit/review actual version; Cancel | F/A; accurate units, integer/decimal validation; maker/checker retained |
| O19 Operator fees | Scoped version list; gross/fee/net explanation tied to actual policy data | Create/view/review/activate supported fee policy | Q/F/A; no new pricing policy or commission invented |
| O20 Fee editor/review | Related percent/fixed/unit/date fields in short sections, explicit affected scope | Save and separate lifecycle review | F/A; don't preview synthetic earnings as actual payouts |
| O21 Scheduling policy | Enabled state, horizon, lead/offer/handoff windows, surcharge/cancel terms displayed coherently | View/edit/create permitted policy; review activation | Q/F/A; scheduling does not become guaranteed assignment |
| O22 Scheduling editor/review | Time units and ranges explicit; cancellation/refund fields conditional on real contract | Save/submit/review actual version | F/A; contradictory windows fail before submit and remain server-validated |
| O23 Fixed-route catalogue | Route label/service/status and directional fare; static detail map, not participant tracking | Create identity; open version/direction; refresh | Q/A; publication distinct from draft save |
| O24 Route identity editor | EN/FR/AR names/descriptions in labelled sections, service/scope | Create/update permitted identity; Cancel | F/A; native RTL fields work independently from page locale |
| O25 Route version/direction/stop editor | Explicit outbound/inbound, ordered stops, bounded geometry rows + static preview, fare link | Add/reorder allowed stops; edit geometry; save draft | F/A; no reverse-route inference or arbitrary JSON; coordinates have correct order/units |
| O26 Route publication/replacement review | Exact version/direction/fare/effective state and change summary | Publish/replace/retire permitted version after review | F/A; no live availability promise from route publication |

## People and eligibility

Source: `StaffAccessScreen.kt`, `DriverRecruitmentScreen.kt`, protected-document
download and driver-application models. Owner-controlled approval policy remains.

| ID / page | Composition and visual choices | Options / genuine actions | Profiles / acceptance |
| --- | --- | --- | --- |
| O27 Staff access | Scoped grant list with actor, rights, expiry and request/decision state | Create/revoke request; review as authorized; refresh | Q/A/P; no badges hiding expiry/manual recertification |
| O28 Grant request | Target identity, scope, bounded permission choices, dates/reason and typed review | Submit request / Cancel | F/A; no self-grant; no uncontrolled scope UUID paste |
| O29 Revoke request | Exact existing grant/target/scope, consequences/reason and typed review | Request revocation; Cancel | F/A; preserve protected minimum-admin rules; not an immediate local revoke |
| O30 Independent grant decision | Request/target/requester/reviewer and effect, clear permitted decision | Approve/reject with existing typed/MFA requirements | F/A; reviewer distinct from requester and target; no command replay after step-up |
| O31 Recruitment queue | Oldest-first application table, status/age/requirements and compact aggregate funnel where returned | Select application; supported filters; refresh | Q/A/P; suppression not zero; no applicant ranking/automated approval |
| O32 Requirement versions | Label/version/status/service with categorized requirements | Create/edit permitted draft; localized copy; review transition | Q/F/A; active requirements not silently changed by form save |
| O33 Requirement editor/review | Typed category/mandatory/data/evidence requirements with multilingual descriptions | Save/submit/review version; permitted add/remove/reorder | F/A; changes summarized; no uncontrolled document request |
| O34 Application review | Applicant-safe identity/vehicle/requirement matrix, credential expiry, submitted evidence metadata | Retrieve permitted protected file; record allowed decision/reason | Q/F/A/P; no PII grid thumbnails; file retrieval recent MFA/no-store/city scope |
| O35 Driver decision review | Exact applicant/city/services/requirements and decision consequence | Approve/reject/request info as supported; confirm separately | F/A/P; human reviewer controls eligibility; no design-driven automatic recommendation |
| O36 Protected-document retrieval | Purpose/status/metadata and one explicit open/download action; failure details safe | Authorized retrieval; Close | Q/A/P; scanning/storage unavailable disables action; no cached inline identity documents |

## Money and actual reconciliation

Source: `PaymentOperationsScreen.kt` and payment models/gateway.

| ID / page | Composition and visual choices | Options / genuine actions | Profiles / acceptance |
| --- | --- | --- | --- |
| O37 Payment overview | Tabs/sections Recipients, Capabilities, Transfers, Refunds; scope/status present | Open real subsection; refresh | Q/A/P; no fake live revenue total or commercial-money acceptance claim |
| O38 Recipient list/create | Meaningful recipient label/method/status; protected detail fields in focused editor | Create actual recipient; inspect version/lifecycle | F/Q/A/P; no unrelated financial credentials; server-owned exact destination |
| O39 Capability list/create | Per-city/operator/method lifecycle and recipient link | Create/activate allowed capability with review | F/Q/A; cash obligations preserved; no card capability created for design |
| O40 Transfer queue/detail | Oldest-first pending/processing records, exact payment reference/amount/method and safe evidence metadata | Inspect; verified/reject command after review; refresh | Q/A/P; claim not verified; zero queue not inferred from failed read |
| O41 Transfer decision review | Exact recorded amount/reference/recipient/ride and consequence, reason | Verify/reject existing action; recent MFA; explicit reconfirm after step-up | F/A/P; conflicting status refreshes; never optimistic paid badge |
| O42 Refund recorder/review | Original payment, prior refunded total, remaining amount, reason and bounded evidence reference | Record actual confirmed refund; review/cancel | F/A/P; no external money movement from browser styling; append-only records |
| O43 Refund ledger/detail | Original fare/payment retained, dated refund rows, total/net and closed reasons | Inspect; refresh; authorized reference copy | Q/A/P; no edit/delete-history affordance |

## Live operations, support, intelligence and security

Source: `ScheduledExceptionsScreen.kt`, `AnalyticsScreen.kt`,
`CaseOperationsScreen.kt`, `AccountSecurityScreen.kt`,
`SecurityIncidentScreen.kt`, `OperationsScreens.kt` audit section.

| ID / page | Composition and visual choices | Options / genuine actions | Profiles / acceptance |
| --- | --- | --- | --- |
| O44 Scheduled exceptions | Age/state-oriented list, booking context/detail, actual exception type | Inspect supported record; refresh; existing permitted action only | Q/A/P; no new manual reassignment/control invented |
| O45 Intelligence overview | Few real aggregate panels with units/window/freshness/suppression; chart/table pair | Select supported scope/window; inspect aggregate detail | Q/A/P; no individual trails, demand heatmap or invented fairness score |
| O46 Aggregate report detail | One metric family per page, explicit denominator/method/data caveats, accessible data rows | Filter supported period; refresh; export only if actual contract | Q/A/P; unavailable/suppressed data not zeros |
| O47 Support/safety queues | Separate purpose-labelled queues, overdue alert strip, assigned owner and next action | Open case; supported filters; assign/triage/review | Q/A/P; ordinary support and urgent safety not a single decorative feed |
| O48 Case detail/timeline | Participant-safe facts, responsible staff, age/deadline, immutable event list | Existing response/triage/transition/handoff actions | Q/F/A/P; private notes not exposed to participant views |
| O49 Support triage/transition | Exact case/action, controlled reason/priority/category fields and consequence | Confirm supported action; Cancel | F/A/P; no silent issue closure; stale case version refresh |
| O50 Safety handoff/transition | Current responsibility, target qualified actor, deadline/reason and review | Explicit handoff/escalate/resolve through existing contract | F/A/P; no implied emergency dispatch or staff selection beyond authority |
| O51 Overdue alert acknowledgement | Alert/case age/state and actor action visible; no celebration | Acknowledge actual alert; return queue | F/A/P; acknowledgement is not case resolution |
| O52 Retention/legal hold | Purpose-scoped retention facts and hold status in isolated detail | Existing hold/release review with reason/MFA | F/Q/A/P; no irreversible purge feature introduced by design |
| O53 Account security | Case-linked exact target UUID input, association-market explanation and controlled action/reason choices | Revoke all sessions, suspend or reactivate through existing reviewed command | Q/F/A/P; no account search/read-detail invented; command authority must cover every target-associated market |
| O54 Account-security command review | Case/target/scope/action/consequence, bounded reason, typed confirmation | Perform authorized reviewed action; Cancel; step-up then re-review | F/A/P; no self-authority or hidden side effects |
| O55 Incident queue/create | Severity/state/owner list; focused create form with real category/scope/context | Create permitted incident; open selected incident; refresh | Q/F/A/P; no private secrets/log dump in narrative |
| O56 Incident detail/responsibility | Current state, primary/backup responsibility, timeline, recovery checkpoint | Assign/reassign permitted responsible actors; inspect change history | Q/F/A/P; append-visible ownership changes, no silent overwrite |
| O57 Incident timeline/event | Typed event/context/date/reference fields and immutable prior entries | Append supported event; review; Cancel | F/A/P; timestamps shown local with explicit zone; no arbitrary JSON |
| O58 Incident transition/recovery | Current→target phase, required evidence/responsibility and consequence | Confirm permitted transition with reviewed prerequisites | F/A/P; no “recovered” badge before server confirmation |
| O59 Postmortem | Structured factual sections, actions/responsibility/dates, clear draft/final state | Save/submit supported postmortem; inspect prior events | F/A/P; no speculative cause presented as verified |
| O60 Audit | Scope/time/action/actor table, expandable read-only detail | Supported filters/pagination; safe exact reference copy | Q/A/P; no edit/delete or raw private payload reveal |
| O61 Restricted/empty/error detail | Reusable C18/C39 region sized to prior content; no dramatic dashboard overlay | Retry/Back/change permitted filter/scope | Q/A/P; explicitly distinguish empty, suppressed, failure and access loss |
| O62 City driver authorization detail | Existing authorization state/expiry/city/services and immutable history | Open only allowed suspend/revoke/reinstate review | Q/A/P; not a generic driver-account state; new work checks current city eligibility |
| O63 City authorization suspension | Authorization/city/expected application version, controlled safety/eligibility reason, full-ID confirmation | Confirm suspend; Cancel | F/A; reason choices follow actual enum; conflict/MFA cannot replay |
| O64 City authorization revocation | Exact authorization and irreversible permission consequence, controlled withdrawal reason | Confirm revoke; Cancel | F/A; full-ID confirmation retained; new application after revocation |
| O65 City authorization reinstatement | Suspended authorization and passed-eligibility review reason with exact-ID confirmation | Confirm reinstate; Cancel | F/A; no locally chosen approved state; backend current eligibility required |
| O66 City-service assignment creation | Exact operator/city, allowed service type and effective interval | Create assignment; Cancel | F/A; timestamps include zone; no overlapping active assignment; not operator status toggle |
| O67 Service-area boundary editor | Version/effective interval, bounded WGS84 longitude-latitude rows and static preview | Create draft boundary; Cancel | F/A; source currently accepts one polygon with automatic closure; no arbitrary multipolygon editor assumed |
| O68 Recipient lifecycle review | Exact recipient/method/version/state/effect and review reason | Verify DRAFT or retire VERIFIED as permitted; Cancel | F/A/P; no pause/activate action; no financial destination silently replaced |
| O69 Payment-capability lifecycle review | City/operator/method/recipient version and current/target state | Permitted activate/retire review; Cancel | F/A; cash obligations and version checks retained |
| O70 Operations MFA recovery-code mode | Masked identity/challenge context and one saved-code field | Verify recovery code; return TOTP mode; Cancel | F/A; no generated replacement code or unsupported SMS flow |
| O71 Safety case detail | Safety-specific category/severity/responsible staff/deadlines/public-private distinctions | Existing handoff/transition/participant-safe response | Q/F/A/P; separate from ordinary support detail; no fake emergency dispatch |
| O72 Retention review detail | Scoped case/report retention facts and legal-hold state | Open allowed hold/release review; refresh | Q/A/P; no purge button introduced; evidence reference minimized |
| O73 Legal-hold placement review | Exact case/hold reason/reference, explicit retention consequence | Place supported legal hold; Cancel | F/A/P; immutable/audited effect and MFA semantics retained |
| O74 Legal-hold release review | Exact existing hold/context, reason and release consequence | Release supported hold; Cancel | F/A/P; release not deletion or permission to expose records |
| O75 Overdue alert detail | Actual linked case, deadline/age/responsibility and acknowledgement state | Open case; acknowledge via O51; refresh | Q/A/P; acknowledgement never equals resolving the case |
| O76 Recipient creation | Actual recipient label/method/typed recipient data, scoped creation | Create recipient; Cancel | F/A/P; separate from list/lifecycle; no credential collection |
| O77 Payment-capability creation | Exact city/operator/method/compatible recipient selection and version | Create capability draft; Cancel | F/A; no local activation or invented card capability |
| O78 Requirement-version lifecycle review | Current/target state and exact requirement version, reason | Submit/activate/replace/retire only as permitted; Cancel | F/A; no silent edit of active recruitment requirements |
| O79 Tariff lifecycle review | Exact version/service/effective interval and current/target state | Permitted submit/review/activate transition; Cancel | F/A; pricing authority and independent review retained |
| O80 Fee-policy lifecycle review | Exact operator policy, fee shape/rate/effect and reason | Permitted policy transition; Cancel | F/A; no local commission change or inferred earnings |
| O81 Scheduling-policy lifecycle review | Exact booking windows/surcharge/cancellation snapshot and transition | Permitted policy lifecycle command; Cancel | F/A; no guarantee implied by activation |
| O82 Route replacement review | Current and replacement published versions/directions/fare links, effect | Replace permitted route version; Cancel | F/A; existing trips retain history/version snapshots |
| O83 Route retirement review | Exact route/version/direction and effect on future discovery | Retire permitted version; Cancel | F/A; no history deletion or active-ride mutation |
| O84 Support triage | Exact case; acting reviewer claims responsibility; LOW/NORMAL/HIGH/URGENT priority; participant acknowledgement; private internal note | Claim and acknowledge; Cancel | F/A/P; no category/assignee selector; distinct from case transition or resolution |
| O85 Safety transition review | Exact safety case/current-target state, controlled reason/public-message fields | Confirm permitted escalate/resolve/close transition; Cancel | F/A/P; handoff remains O50; state transition not emergency dispatch |

## All modal, drawer, selection and table options

Every editor has separate Save draft/Submit/Review/Activate controls only when
the documented lifecycle permits them. A neutral read drawer can close by Escape
or Back with focus returned to its launcher. A dirty editor warns before losing
safe edits. A command dialog cannot be dismissed in a way that implies success;
uncertain outcomes reconcile. Drawer footer never covers reasons/terms at 200%.

Scope selection, compatible-record choices, status filters and service choices
use loaded labelled options. Long labels wrap; exact identifiers are available
in an explicit audit/detail region, not a user-facing main selection label.
Lists never silently fetch a broader scope to populate a pretty empty layout.

Table columns prioritize human identity/context → state → meaningful date/age
→ amount/version → action. On narrow screens these become labelled record cards,
not horizontally clipped data. Pagination states actual shown/returned counts;
do not add search/sort/exports unless backed by a real query/API contract.
Keyboard focus, selected record and scroll position survive ordinary read refresh;
scope/session changes intentionally clear protected detail.

## Further source reconciliation

| ID / page | Composition and visual choices | Options / genuine actions | Profiles / acceptance |
| --- | --- | --- | --- |
| O86 Selected city detail | Localized names, code/timezone/centroid, lifecycle, actual assignments/config versions and readiness navigation | Open service-area/config/readiness; allowed lifecycle review; Back to cities | Q/A; selected scoped record is a distinct review composition from O06 list; no inferred activation |
| O87 Readiness decision review | Exact gate/config revision, independent-review explanation, passed/failed choice and safe evidence reference | Record decision; Cancel | F/A/P; evidence 3–240 characters; maker cannot review; owner/dates are in the referenced evidence, not invented API fields |

## Alpha versus full redesign coverage

Design all listed pages now so no later work invents a second identity. Implement
alpha public/auth/application/queue/review and representative city/driver/cash
operations first, using the exact same system. Reuse foundation improvements
across the 14 existing destinations, then complete the remaining detailed editor
polish in later waves. The alpha demonstration must identify any secondary
destination that still awaits final native/browser acceptance; no “fully
redesigned console” claim is made from one representative screenshot.
