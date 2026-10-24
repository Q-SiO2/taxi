# Protected web localization — implementation and acceptance

## Current checkpoint — 19 October

Hosted [v8](board-alpha-evidence/candidate-web-v8.json), deployment
`ceee310c-e957-49ad-945d-b9f2d292eb61`, now contains the coherent WL-3/WL-4
presentation packet: rollout, recruitment/applicant, payments, support/safety and
scheduled-booking display. The exact source validation passed 75 browser tests
and 1,218-key EN/FR/AR catalog checks. The completed optimized build reused those
test results; it is not a second fresh run. Eight packaging tests and
[102 hosted checks](board-alpha-evidence/hosted-web-v8-20261018-oct19-first.json)
pass against 93 exact assets. Existing commands, authority and wire codes remain.

[Actual applicant Save/Submit](board-alpha-evidence/v8-applicant-save-submit-20261019.json)
passes on the preserved profile-only draft: saved revision 2 and submitted
revision 3, independently read back. Normal reviewer MFA succeeds and the
explicitly approved expiring Casablanca roles are available. The matched reviewer
correction and applicant resubmission now pass at revision 7, including explicit
session-expiry recovery. Arabic support claim/acknowledgement and participant
readback confirm separate internal/public notes. Remaining case/booking/payment
visual states remain runtime acceptance work, as do the
complete style/language/responsive and accessibility matrices. The atlas remains
267 declarations / 59 files / 213 views, not accepted-page coverage. Native v11
inputs are frozen to the paired v8 source plus one test-only assertion correction.
Its APK configuration and 353 JVM / 291 Android-host tests pass; two trips remain required.
Its first runtime trip then fails completion-location acquisition and is explicitly
rejected in [the native failure record](board-alpha-evidence/native-v11-runtime-rejection-20261019.json).
That failure does not alter the independently frozen live web v8 package. Later
actual v8 booking terms retain the same scope/policy across AR/FR/EN and Notepad;
payment empty-state guidance also passes all three languages. Populated financial
flows, the full visual matrix and accessibility remain separate gates.

The native completion repair is now frozen as v12 with 355 JVM / 291 Android-host
checks and exact staging/map-only APK configuration verification. Its first clean
French full trip passes booking through confirmed cash; the earlier failed Start
attempt and two separately qualified recovery records remain archived. These
native-only callback/test changes do not alter web v8's frozen input manifest.
Arabic v12 completion then exposes an Android request-ownership gap, with both
lookup attempts preserved as failures. Native v13 now passes 356 fresh JVM / 291
fresh Android-host checks and exact APK configuration checks. Its priority repair
and retry test change no web resources or contracts. Native recovery/rehearsal
remains separate from the independently frozen web v8 acceptance scope.

## Historical checkpoint — 18 October

Hosted [v7](board-alpha-evidence/candidate-web-v7.json), deployment
`7e30999d-719b-4f84-bda0-8bf45baccc2a`, passes 71 fresh browser tests, eight
packaging tests and [102 hosted checks](board-alpha-evidence/hosted-web-v7-20261018-client-headers.json).
[The protected runtime record](board-alpha-evidence/wl3-hosted-v7-protected-review.json)
indexes nineteen actual JPEG captures. Scoped recruitment/review, privacy hiding,
RTL actions and an Arabic unsent draft retained through French and all four styles
are evidenced. A submitted applicant remains selected across FR/AR/EN; Arabic
withdrawal review opens and cancels without changing its submitted state.

This is partial WL-3 acceptance. Editable writes, requirement transitions,
protected documents, full style/locale matrices and accessibility remain open.
The [post-v7 source checkpoint](board-alpha-evidence/wl4-overview-polish-source-20261018.json)
corrects dark-header refresh contrast, dense queue dates, style copy and the MFA
success notice, and translates the read-only rollout overview. JS/Wasm compilation,
72 browser tests and 988-key EN/FR/AR validation pass. This source is not in v7.

An [actual editable rehearsal](board-alpha-evidence/wl3-v7-editable-contract-failure.json)
then created a complete profile-only draft but failed to save: omitted empty
answer/evidence arrays produced a version-only PATCH, correctly rejected with 422.
The draft remains `NOT_STARTED`, revision 1. Preserve the failure and retest the
corrected transport in the replacement UI before claiming editable acceptance.
The [source fix](board-alpha-evidence/recruitment-wire-source-fix-20261018.json)
passes three real HTTP serialization regressions after reproducing the missing
array failure; eight backend unit tests pass. Its test-only MockEngine uses the
existing Ktor version and adds no application runtime dependency. No new UI pass
is inferred.
Keep v7 frozen while its replacement is prepared; do not relabel its captures.

The [payment source checkpoint](board-alpha-evidence/wl4-payments-source-20261018.json)
adds complete resource-backed payment forms/feedback, display-only status/action
labels, mixed-script draft typography and isolated money/reference/date values.
JS/Wasm compilation and 73 browser tests pass in 6m50s; 1,063 EN/FR/AR keys
validate. Commands, grants, scope, version/idempotency rules and backend payment
authority are unchanged. This remains source-only: actual payment views and
states, support/trip presentation, replacement-browser Save and final native
rehearsals are unfinished. The atlas currently verifies 265 declarations in 59
files and retains 213 views; it does not establish their visual acceptance.

The [case/booking source checkpoint](board-alpha-evidence/wl4-cases-bookings-source-20261018.json)
then completes the bounded WL-4 translation source: support/safety queues and
details, note visibility, controlled case/retention consequence dialogs and
feedback, plus scoped booking exception states, snapshotted economics and linked
live-ride references. Fixed dialog width floors are removed and selected-style
radii/mixed-script fonts applied. Unknown refund policies remain unavailable;
they never imply non-refundability. Permissions, scopes, visibility, payloads and
server authority remain unchanged.

JS/Wasm compilation and 75 browser tests pass in 5m26s; 1,218 EN/FR/AR keys
validate. The source atlas passes at 267 declarations in 59 files / 213 views.
[V8 build inputs](board-alpha-evidence/web-v8-build-inputs.json) freeze the 411
validated source/build files for optimized release preparation. V7 is still live.
No WL-4 actual view, protected write, full style/locale or accessibility acceptance
is inferred. Retest the preserved applicant draft through the replacement UI,
then verify the scoped case/booking/payment views before the final native freeze.

## Earlier entry checkpoint — 17 October

The hosted candidate at this checkpoint was [web v6](board-alpha-evidence/candidate-web-v6.json),
deployment `72a8722f-c230-4de3-9126-cd9d72ec1d29`. Its 67 browser tests and
[98 asset/boundary checks](board-alpha-evidence/hosted-web-v6-20261017.json) pass.
[Actual runtime checks](board-alpha-evidence/wl2-hosted-v6-session-recovery.json)
verify grayscale Notepad, French MFA failure/scroll/cancel, successful fresh
French and English MFA, and explicit Casablanca retention across EN/FR/AR.
The captured content sizes are 665×524 and 1280×720 pixels; these are actual image
dimensions, not an inferred CSS/device viewport.

This clears the functional entry/recovery checkpoint for protected translation
work. WL-2's remaining desktop bounds, keyboard/screen-reader/large-text and
motion checks remain open acceptance gates. The desktop review exposed ineffective
`fillMaxWidth().widthIn(...)` ordering; source now applies the bound before fill,
requiring a new build/render. Protected rollout text is still English, with ratios
reordered in RTL; WL-4 must translate display labels and isolate numeric counts.

WL-1 has local source, build and actual browser evidence in
[the local record](board-alpha-evidence/wl1-local-browser.json). EN/FR/AR choices,
Arabic RTL, persisted language, readable Arabic options while French is active,
and retention of unsent operations/applicant identifiers passed. The existing
resource system updates without `key(language)`, coordinator replacement or
session reset. Storage/adapter failures retain an explicit recoverable state.
The external `locale.js` preserves the existing CSP. Authenticated session/scope
retention now has a scoped hosted result described below.

WL-2 entry and shell source compiles for JS and Wasm. Its initial 62-test browser
suite and subsequent 67-test suite (18 suites, zero failures/errors/skips) passed.
Operations sign-in/MFA/navigation/scope and applicant
sign-in/register entry use shared EN/FR/AR resources, concise copy, directional
credential fields and accessible labels. Existing shared abstract graphics now
appear in the web entry panels. Local Arabic and French applicant renders show
live Casablanca catalog data; an unsent Arabic name survived switching to French.
These are local development JS checks, not a deployed or authenticated acceptance.

The compact-width check exposed applicant draft loss across the desktop breakpoint.
The draft now lives above responsive branches, in short-lived memory only. Actual
390-to-1280 width changes preserve it, and the Arabic form shows translated local
validation with its main action reachable by scrolling. A mixed Arabic name showed
missing glyphs while English was selected; its web-only correction now passes an
actual render containing French accented and Arabic characters together. The
[local record](board-alpha-evidence/wl2-local-browser.json) identifies the final
90-file development bundle and keeps earlier screenshots labelled by phase.
New resource-backed entry/error messages and contextual catalog retry compile and
their policy tests pass. A generic 503 no
longer establishes a document-storage failure or a claim that no file was accepted.
Public catalog, generic service outage, unknown command outcome, authorization and
conflict recovery have separate presentation mappings. The catalog now contains
730 keys in EN/FR/AR. This validates catalog coverage, not every protected view.
Fresh French password/MFA sign-in passed on hosted v5. Explicit Casablanca scope
remained selected through Arabic, English and French changes without another
sign-in; [the record](board-alpha-evidence/wl2-hosted-v5-session-scope.json) identifies
the exact deployment and screenshot hashes. This is shell/session evidence,
not complete protected-page translation or a network assertion of zero commands.
Remaining accessibility/responsive checks are required before closing WL-2. Popup semantics appeared
stale after dismissal in the local browser; do not infer screen-reader acceptance
from screenshots or labels alone.

The preview permits only the exact live compatibility and recruiting-cities public
GETs, records method/path metadata, and refuses auth/domain writes. It supplies no
fake city, session, document or trip success. At that checkpoint Railway served optimized web v5,
deployment `62985a05-46c3-4b74-8bcd-d101f003e18b`; all 93 assets and five anonymous
boundaries pass. The hosted review exposed two entry/style defects: a lavender
Material dialog in Notepad and cancel clipped by MFA errors in a short viewport.
Source fixes map the remaining Material surface roles and enable MFA scrolling.
They require a new candidate and actual render; v5 and native v9 remain immutable.
Protected
recruitment/applicant records and board operations remain WL-3/WL-4 work; the full
web application is not yet accepted as trilingual.

## WL-3 source checkpoint — recruitment overview

The [first source slice](board-alpha-evidence/wl3-source-slice1.json) translates
recruitment entry and privacy-preserving funnel labels, reuses the shared status
resource mapping, selects city copy in the current language and isolates visible
counts. It never reconstructs suppressed values. The 755-key catalog validates;
JS/Wasm source compilation and 67 browser tests pass in 4m46s. Test XML is archived.

The [18 October recruitment checkpoint](board-alpha-evidence/wl3-recruitment-source-20261018.json)
adds requirement administration, editors/transitions, application review and city
authorization consequences. JS/Wasm compilation, 69 browser tests and two focused
shared JVM tests pass; its 895-key catalog validates.

The [combined protected source checkpoint](board-alpha-evidence/wl3-protected-source-20261018.json)
then adds the applicant dashboard, editor, documents, vehicle form, timeline,
withdrawal and resource-backed loading/validation/confirmed-action feedback.
JS/Wasm compilation and 71 browser tests pass; 950 EN/FR/AR keys validate. It
preserves command payloads, scoped access, version checks and backend authority.
Source/runtime acceptance remain separate. The final v7 build inputs are frozen
in [their own manifest](board-alpha-evidence/web-v7-build-inputs.json), including
an additional identifier-isolation adjustment and stronger editable-draft test
fixtures. The [optimized v7 package](board-alpha-evidence/candidate-web-v7.json)
now passes 71 fresh browser tests and eight packaging tests, with 93 assets /
29,060,729 raw bytes and no source maps. The reviewed packaging budget change
has [separate immutable inputs](board-alpha-evidence/web-v7-packaging-inputs.json).
It is deployed to staging and all 102 hosted checks pass. The protected runtime
record at the top defines the narrower actual UI acceptance scope.

Full view/flow acceptance remains open. The
[Arabic v6 baseline](board-alpha-evidence/wl3-v6-ar-recruitment-before.png) still
shows the old English body and is historical. V7 now has actual Arabic/French
review, mixed-script draft and withdrawal-consequence captures. Writes and complete
desktop/MFA/accessibility acceptance still require proof. The source atlas
verified all 213 views at that checkpoint, with 263 declarations in 59 files;
that is source coverage, not per-view acceptance. The current count is above.

V7's successful MFA reverify notice still uses English. Its source correction is
included in the 988-key checkpoint above; an actual replacement-runtime retest
is required. Do not call the full web demo trilingual yet.

## Outcome and authority

The owner requires English, French and Arabic in the demo, with concise copy.
The first native welcome matrix passes; operations/applicant web still has
English literals. Do not call the whole demo trilingual until the actual web
journeys pass. This packet implements A-07/A-10 under the active
[board checkpoint](../board-alpha.md); it adds no backend architecture or role.

Preserve server authorization, scope, MFA, version/consequence review and payment
authority. Language is a local presentation preference, like style. Never send
it as identity, recreate coordinators, clear the current review, lose safe drafts,
replay commands or bypass a required re-review to change text direction.

## Bounded implementation order

| Packet | Source boundary | Checkpoint |
| --- | --- | --- |
| WL-1 Locale boundary | Existing web entry point plus shared/platform resource adapter; three explicit language choices and persisted fallback | Switch language on an unsent login draft and authenticated read view without domain calls or coordinator recreation. Refresh retains language. Blocked storage gives a visible temporary choice. |
| WL-2 Entry and shell | Operations/applicant sign-in, MFA, navigation, scope controls, common cards/dialogs/table labels | Remove long implementation/provider copy from the normal flow; retain concise access and MFA instructions. FR/AR/EN keyboard entry and narrow/desktop layouts pass. |
| WL-3 Recruitment and applicant | Recruitment queue/review, requirements, onboarding funnel, applicant application/editor/status | Translate status/reason display labels while retaining unchanged wire enums. Preserve version checks, protected evidence and applicant-safe message boundaries. Review/actions remain reachable in Arabic. |
| WL-4 Board operations | Representative trip, support and cash/payment records; errors/loading/empty/conflict/unknown outcome | Every view actually shown has complete translated states. Server money/status and role restrictions remain exact. No English-only consequential dialog in an Arabic/French demonstration. |
| WL-5 Remaining web inventory | Remaining operations/applicant screens from the 213-view ledger | Scan each source-backed view for unexternalized user-visible literals and unmapped enum/error labels. Record deferred surfaces explicitly; no blanket acceptance from shared tokens. |

Complete one packet with focused tests and actual browser renders before starting
the next. Build shared web changes once per coherent packet, since the complete
JS/Wasm release optimization is costly on this host. Keep the running verified
staging candidate available until its replacement passes.

Shared web resource additions also alter the native package. Use focused tests
and the actual critical renders for intermediate packets; freeze the final
native/web candidates after WL-3/WL-4 presentation resources settle. Spend the
required two complete native trip rehearsals on that final freeze. The passed
v9 native trip is baseline evidence and does not become a pass on newer APKs.

The same final shared polish must repair the reviewed native confirmation-button
contrast/style defect indexed in board-alpha.md. Preserve its fare/date context
and server-owned command; do not infer component readability from a passing
palette test alone.

## Implementation constraints

Use the existing Compose resource structure, not a second translation framework
or runtime translation service. Add reviewed `values`, `values-fr`, `values-ar`
resources and generated accessors. Keep style option names as the selected names.
Translate display labels rather than backend keys, IDs, submitted evidence,
free text, reason codes or API payloads. Preserve exact fare/payment distinctions.
Map known backend errors to localized actionable copy and retain a safe generic
fallback; do not expose raw protected payloads as a translation shortcut.

Check the installed Compose version before implementing the locale adapter.
The current [JetBrains locale guidance](https://kotlinlang.org/docs/multiplatform/compose-resource-environment.html)
uses platform adapters while a common public locale API is unavailable. Its
example keys content by locale; this application must preserve coordinators and
safe drafts across language changes, so do not copy that root-key behavior.
Any browser locale override belongs in application code with explicit ownership
and tests, not hidden browser automation state. Respect the existing CSP.

Provide RTL layout at the presentation boundary. Mirror start/end layout and
directional navigation, preserve phone/email/code entry direction, and isolate
identifiers, currency/numbers and mixed-script values. Replace unsupported text
glyphs in dropdown chrome with existing vector icons; visible missing-glyph
squares do not pass acceptance. Do not mirror map geometry or invent addresses.

## Exit evidence

- Focused tests for persisted/unknown/failed-storage locale, draft retention,
  scope/session retention and zero domain commands on language/style changes.
- Actual FR/AR/EN login, MFA, scoped recruitment queue/review, applicant status,
  representative trip/cash/support and each consequential dialog shown.
- Compact and desktop layout, keyboard/focus, screen-reader labels, large text,
  explicit errors and bidi amounts/identifiers checked.
- Exact JS/Wasm artifact manifest, hosted proxy/session/MFA result and fresh
  screenshots after deployment. Redact secrets; use the synthetic cohort only.
- Update A-07/A-10 and the actual per-view ledger. Keep physical/native and
  pilot/public gates separate. No accepted view may inherit an unverified status
  solely because its parent or shared theme passed.
