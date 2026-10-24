# Delivery sequence, evidence and owner approval

## Board alpha execution authorized — 15 October 2026

The owner now directs the earliest functional board alpha, authorizes application
implementation and TaxiMobile Railway staging changes/deployment, and requires
French, Arabic and English with concise copy. This supersedes the earlier
planning-only stop. The selected four-style contract remains in force; no further
palette approval is needed. Follow [the active board alpha checkpoint](../board-alpha.md)
for execution and evidence. Native, integrated staging, device and release
acceptance must still be demonstrated.

**Status: four-style direction selected; native rollout and release acceptance pending.**
The owner selected Folded Streets, Street Press, Glazed Machine and Notepad as
user options. The earlier wait for visual-direction selection is resolved for
this style set. [style-options.md](style-options.md) defines ST-0–ST-4 before and
within the existing UX waves. Native/device and release evidence remain open.

## Proposal to approve

| Decision | Recommended starting choice | Concrete alternatives |
| --- | --- | --- |
| User-selectable styles | Folded Streets / Street Press / Glazed Machine / Notepad | Owner-selected set; no independent color-theme menu |
| Typography | T1 Inter + Noto Sans Arabic | T2 Plus Jakarta Sans + Noto Sans Arabic; T3 IBM Plex Sans + IBM Plex Sans Arabic |
| Passenger navigation | Ride / Trips / Account with dedicated secondary pages | Map account-menu navigation; requires a revised page navigation map before implementation |
| Driver navigation | Work / Earnings / Account; current job dominates active state | Work + compact account menu; do not bury cash recovery or current offers |
| Visual finish | Art-free interface language with scoped abstract fields | Gradients / collage / grain inside the expressive styles; Notepad keeps grayscale rules/icons and no decorative performance |
| Alpha location choice | Map selection; no apparent search provider | Provider search only after endpoint/license/coverage acceptance |
| Delivery scope | Full design now, core journeys + representative operations implemented first | Entire console polish before alpha adds time without proving core taxi flow |

The board is a comparison specimen, not a working app. Its schematic maps,
synthetic fares/times/counts and illustrative driver identity do not imply that
providers, continuous tracking or financial settlement are accepted. Selecting a
board option does not submit approval or change app settings.

**Owner approval record:** Four-style direction and user selection approved;
recorded 15 October 2026. Independent color themes abandoned. Main illustration
not selected. Notepad requested as grayscale, task-first, with meaningful icons
and decorative animation off. No new palette approval is required. Typography,
component engineering, native view/device acceptance and release decisions are
tracked through the selected contract and the waves below.

## Complete coverage and realistic boundaries

The page books and [visual atlas](page-atlas.html) specify 112 mobile design
surfaces (including nine explicitly deferred capability surfaces), 101
applicant/operations surfaces, and 40 shared product components with a
[visual gallery](component-gallery.html). These are design rows, not 213 new routes. Existing APIs,
dialog/state views and reusable pages carry most of that coverage. Every page
inherits global/state profiles and concrete component options. A developer may
not interpret omitted copy in one row as permission to invent a different style.

Each row now has a separately authored visual composition and standalone
specification under `pages/`; [coverage.md](coverage.md) is the complete ledger.
The refreshed source audit covers 261 named Compose declarations in 58 files, classifying
helpers/components separately. [Wave assignment](wave-assignment.md) assigns every
design ID exactly once, including the added secondary views. Approval of the
whole design is distinct from native acceptance of each delivered wave.

The full scope is designed now to prevent drift. The shortest path to A is to
implement and accept the complete essential booking/offer/trip/cash story first,
then support/account/applicant and representative operations. Fixed routes,
scheduling/manual transfer and secondary administration get coherent styling
through the same foundation; their own capability and rehearsal gates remain.
Designing deferred surfaces does not authorize their backend implementation.

## Work waves after approval

Estimates below are focused engineering days for one engineer with existing
backend contracts retained. They are planning ranges, not dates/promises. Native
render quality, translation review, new defects and approval turnaround affect
elapsed time. No parallel agent work or framework migration is assumed.

| Wave | Deliverable / exact implementation scope | Dependencies | Focused days | Acceptance and stopping condition |
| --- | --- | --- | --- | --- |
| UX-0 Approval and reconciliation | Apply the selected four-style contract and preference model; update ui/design/extended_ui/operations visual clauses; reconcile current source/capability inventory; freeze reference/spec revision | Recorded four-style selection; candidate/source baseline | 1–2 | No competing old/new normative instructions; all requested changes accounted for; exact candidate/dirty changes identified |
| UX-1 Foundation and gallery | Semantic light tokens, bundled licensed fonts, type scale, icon consistency, C01–C08/C16–C19/C22/C38–C40; remaining component states mapped in gallery; no fake API integration | UX-0 | 3–5 | Actual Compose Android and web renders of auth/R05/R11/D13/D21/O34; EN/FR/AR, narrow/large text; fix structural failures before more screens |
| UX-2 Auth and passenger booking | S00–S11/S13, R00–R03/R05–R10/R15/R16/R38/R41, development-only R42; split monolithic render responsibilities, keep coordinator/gateway authority | UX-1 | 4–6 | Sign in → select destination/pickup → authoritative quote/request → matching/unmatched/cancel; correct offline/unknown outcome; no dead search |
| UX-3 Assigned journey and receipt | R11–R14/R17/R18/R21–R23/R36/R37; authorized map/identity, final fare/cash distinction, active restoration | UX-2 | 3–5 | Passenger understands actual phase/vehicle/fare/payment; restart/expiry/route failure truthful; no live-supply leak |
| UX-4 Driver core and cash | D07/D10–D25/D38/D41, C13–C15/C20/C21; offers/navigation/arrival/start/complete, independent pending cash recovery/earnings | UX-1 and UX-2/3 integration | 4–6 | Real private offer acceptance → lifecycle → cash settlement → queue/earnings restart; expired/conflicting offer fails closed |
| UX-5 Account, support, applicant | R30–R35/R39/R40/D00–D06/D28–D33/D35–D37/D39/D40/S12/S14–S19/A00–A12; document capability truth; support timeline; read-only history/account facts | Core shell/components | 4–7 | No rejected chrome on reachable alpha pages; no fake verification/upload/support response; participant privacy intact |
| UX-6 Representative operations | O00–O04/O05–O16/O31/O34–O36/O37/O40/O41/O47/O48/O60/O62–O67/O70/O71/O75/O84–O87; foundation applied to all existing destinations, deeper editors queued coherently | UX-1, real scoped records/roles | 4–7 | Scope → application review → driver authorization → trip/payment/case record; actual MFA/independent review/conflicts/keyboard narrow UI |
| UX-7 Alpha visual + integrated acceptance | Fix observed UI/behavior defects, actual devices/browser, localization/accessibility, reproducible synthetic presentation and fallback/disclosures | UX-2–UX-6 | 3–5 | Owner accepts real screenshots and complete repeated journey; A gates remain evidence-driven; no source/test-only “finished” claim |
| UX-8 Secondary workflow completeness | R24–R29/D14/D26/D27/R19/R20; O17–O30/O32/O33/O38/O39/O42–O46/O49–O59/O61; driver dark polish | Alpha core accepted | 8–16 | Full current capability console/mobile visual parity plus secondary lifecycle evidence; no dormant deceptive actions |

UX-0–UX-7 total **26–43 focused days**; UX-8 adds **8–16**. The 13 October source reconciliation expands security, account and secondary
review breadth; the ranges were widened accordingly. Some foundations
reduce later work, but no optimistic overlap is counted. This should be reconciled
against the original 4–8 week target: the low end can fit; full breadth at the high
end can exceed it. Do not promise a public launch date from this UI estimate.
If the window tightens, defer secondary polish/dormant capability UI explicitly;
do not cut authentic booking, offer safety, cash recovery or readable core screens.

## Implementation ownership and file boundaries

| Work | Existing source area to inspect/change after approval |
| --- | --- |
| Theme/fonts/components | `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/`; shared `composeResources`; existing asset/license inventory |
| Shared shell/auth/session | `App.kt`, `feature/app/TaxiMobileScreen.kt`, `AppUiState.kt`, `MobileAppCoordinator.kt`, `feature/auth/`; preserve LocalSessionLifetime fencing |
| Passenger | `feature/passenger/PassengerHome.kt`, current form/ride/place presentation; move task views into focused feature files, keep intents/domain gateway contracts |
| Driver | `feature/driver/DriverHome.kt`, onboarding, offers/ride/cash/earning presentation; preserve server timing and foreground observation provenance |
| Native map/input/insets | Existing Android/iOS map, current-location requester and native entry points; no new provider/background tracking by design fiat |
| Applicant/operations | Existing `webApp/src/webMain/kotlin/org/example/taximobile/applicant/` and `operations/` UI/model/state; preserve separate roots and permission gates |
| Localization | Existing EN/FR/AR resources; contextual copy and translator review; no English labels patched directly into feature code |
| Verification | Existing common/JVM/Android-host/script/backend tests for changed behavior, plus actual device/browser evidence; focused meaningful regression |
| Normative documentation | ui/design/extended_ui/operations clauses, roadmap/implementation/testing/union_demo; references and limitations versioned |

No database migration, backend business-rule change, framework addition or
provider swap is authorized by this visual proposal. If a screen needs data the
API does not supply, explain the missing contract and keep that option absent or
deferred. Preserve all existing dirty user work; inspect diffs before each slice.

## Review packet before broad implementation

The current proposal already supplies all 213 individual browser compositions.
The six-screen packet below is an early native implementation checkpoint after
approval, not a substitute for complete design coverage.

After UX-1, render six critical compositions in actual Compose: S03 sign-in,
R05 review, R11 assigned, D13 offer, D21 pending cash, O34 application review.
Include their failure/stale/busy variants, French long strings and Arabic. Owner
selection of the four styles is recorded; ST-1/ST-2 define the scoped foundation work. Actual renders establish whether
the chosen identity survives the platform. Fix the packet before building a
large page family. Review is a milestone, not a fresh permission prompt per edit.

The browser board demonstrates the four selected style grammars, motion and structure.
It does not replace the native packet, show live dispatch, or prove iOS acceptance.

## Objective visual acceptance

| Check | Required evidence |
| --- | --- |
| Contrast | All actual normal/hover/focus/pressed/selected/busy/error text pairs ≥4.5:1 (large text ≥3:1); required graphical controls ≥3:1; unrounded thresholds; review map halos/opacity |
| Token preflight | [33 static pairs](contrast.md) pass the selected thresholds; [raw values](contrast.json) retained; Graphite/Lime edge exception explicitly outlined |
| Touch/focus | Measured 48 dp minimum native actions and separated fixed driver buttons; full web keyboard path/focus return; no hover-only action |
| Layout | 320/360/430 dp mobile, 360/768/1024/1440 px web; text 1×/1.3×/1.6×/2× and web 200%; keyboard/insets; no clipped essential name/amount/status/CTA |
| RTL/type | Actual bundled fonts loaded; Arabic shaping/diacritics and mixed plates/numbers; mirrored chrome; maps/logos unmirrored; human translation review |
| Motion | OS reduced-motion honored; no moving essential targets; loading indication tied to actual request; success only after server response/reconciliation |
| Outdoor/night | Physical Android bright-light/mounted parked-vehicle review; night/dark review for driver; no claim from desktop contrast alone |
| Performance | Measure current candidate on target lower-end device, then compare frame/jank/startup traces for map/sheet/list/offer; investigate visible regressions, no invented benchmark pass |
| Privacy/truth | No nearby supply before acceptance, secrets/document preview leakage, raw UUID primary copy, implied payment/eligibility/assignment or unsupported control |
| Recovery | Same work/receipt/cash facts after refresh/restart/session expiry; pending command reconciles; read failure not empty success |

## Usability rehearsal after visual approval

Proposed formative sample: five passenger participants, five licensed drivers
and two operations reviewers, recruited with owner/operator approval. This is
a design diagnostic sample, not statistical proof or real-world transport.
Synthetic accounts/records/money only; parked driver-device use for UI tasks.
French/Arabic coverage and access needs must be represented. Consent, minimized
notes and safe records belong to the existing evidence process.

Tasks: passenger chooses map destination/pickup, understands estimated fare/method,
requests, recognizes matching/vehicle/arrival, retrieves pending/completed receipt
and help; driver diagnoses online block, reads/accepts a valid offer, rejects expired
one, performs permitted trip phases, confirms cash, then finds recovered queue/
earnings after restart; operator selects scope, reviews application/decision, finds
payment/case/audit facts without violating reviewer independence.

Record task completion without developer coaching, mistakes, assistance and
participant explanations of fare/status/payment. Proposed alpha exit: no critical
misinterpretation of identity, payment or ride phase; at least 4/5 in each mobile
group complete the core tasks without coaching after fixes; both operators follow
scope/review correctly. These are proposed local acceptance targets, not measured
results or universal usability claims. Any critical failure reopens that screen.

## Test and evidence sequence

1. Validate docs/tokens/font notices and reconcile supported contracts.
2. Run focused behavior tests for changed intent routing, drafts, command gate,
   quote invalidation, session/offer timing and recovery. Avoid tests that merely
   repeat CSS/token values or screenshot every meaningless variation.
3. Compile shared/native/web targets; verify semantics and actual representative
   renders with the candidate identity. Run backend tests only where integrated
   behavior/contract changes justify them; UI polish is not a backend rewrite.
4. Complete real scoped synthetic API→database→client integration and restart/
   network/MFA conflict cases; keep source/component evidence distinct.
5. Capture native/web packets and owner review. Run repeatable full presentation
   twice from documented reset, with honest offline/provider fallbacks.
6. Record candidate commit or dirty tree/artifact hashes, device/OS, locale, font
   scale, scenario/time, defects, reviewer and limitations. Never include credentials,
   government documents, personal location trails or private cases in the packet.

## Roadmap gates and public launch

This plan refines A-02 visual review, A-03 passenger, A-04 driver, A-07 operations
and A-10 rehearsal in [roadmap.md](../roadmap.md). A-08/A-09 hosting/integration
continue only after resumption is authorized and current provider/candidate
standing is rechecked. Prior builds and partial deployments remain dated evidence.
No alpha gate is accepted by this plan, the browser board or token calculations.

B still requires actual operator/city/transport/fare/privacy/payment decisions,
provider acceptance, secure documents, support responsibility and field trials.
C still requires pilot outcomes, distribution/security/accessibility/operations
acceptance and sustainable economics. UI work accelerates the presentation path;
it does not waive those launch obligations. Full detailed acceptance stays in
[gaps.md](../gaps.md), [testing.md](../testing.md) and domain authorities.

## Handoff after style selection

The owner explicitly selected the four-style system. Do not ask for another
palette vote or treat clicking a review control as the source of approval; the
typed owner instruction is recorded in [style-options.md](style-options.md).

The next engineering packet is ST-1 at the existing theme boundary, with source
baseline/candidate identification and ST-2 native proof before broad rollout.
Use one semantic component system with four style treatments, rather than four
copies of each workflow. The shared source renders then feed UX-2–UX-8. The prior
illustrator/vehicle-model production add-on is superseded; hero art and a 3D engine
are not prerequisites on the alpha critical path.

The earlier day ranges predate this four-style selection and must be re-estimated
from the ST-1/ST-2 source/native proof; do not promise those as calendar delivery
for the expanded style acceptance matrix. Alpha still prioritizes the complete
booking/offer/trip/cash story and representative operations before secondary console
polish. Deployment, provider, device/rehearsal and release acceptance remain their
own gates. No additional domain capability or infrastructure change is implied.
