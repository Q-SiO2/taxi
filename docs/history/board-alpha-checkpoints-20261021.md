# Historical board-alpha delivery checkpoints

Archived on 21 October 2026. [The active checkpoint](../board-alpha.md) supersedes all current/next/accepted language below. These are dated observations and failed attempts, not current release acceptance. Relative links have been relocated; the original document SHA-256 was `20d5a7d86d30893b60871a35b62a28a8091c00fe6921595828cf25045cd36a7b`.

# Board alpha — active delivery checkpoint

## Current checkpoint — 20 October 2026

**Current freeze: native v17.** [The exact candidate](../redesign/board-alpha-evidence/candidate-native-v17.json)
passes 372 fresh JVM / 305 fresh Android-host tests with no failures, errors or
skips. Three native source deltas retain only quote inputs and stable credential
ownership, reread fresh server terms, and keep realtime token-specific generation
behavior. Eight new common regression cases include quote/history token rotation;
the focused suite passes 74 checks. Actual quote-resume, two new integrated trips,
same-instance rebooking and current presentation checks are underway. No build
result alone accepts them. Live web v8 / API v6 remain independently deployed.

**Latest runtime rejection: a v16 second-booking quote disappeared during
dashboard catch-up before the observed Request tap reached the API.**
[The rejection](../redesign/board-alpha-evidence/native-v16-quote-refresh-rejection-20261020.json)
preserves the one-time input, actual screens and Railway trace; independent owner
reads find no new ride. V16's first complete cash trip and actual history/support
checks remain scoped passes. The next correction retains session-owned quote
inputs and rereads current server estimates/routes on catch-up, clears intent on
owner/new-primary changes, and never replays ride creation. A replacement freeze
and two complete native runs remain required; v16 is not final acceptance.

**Previous corrective freeze: native v16.** The [v16 manifest](../redesign/board-alpha-evidence/candidate-native-v16.json)
records 412 archived inputs, 364 fresh JVM / 297 fresh Android-host tests and
both staging/map-only APK hashes. The six new common history regressions pass;
the original focused suite was red in four cases and is now green at 55 tests.
The coordinator retains only session-owned navigation identity and fetches fresh
authorized detail/receipt/feedback on refresh. It clears old intent on logout,
new primary journey or revoked detail access and fences late old-session reads.
Actual v16 [passenger history/support](../redesign/board-alpha-evidence/v16-native-passenger-history-support-review-r2.json)
and [driver history](../redesign/board-alpha-evidence/v16-native-driver-history-review-r4.json)
now survive same-process foreground catch-up and a further 15-second wait.
The paid historical receipt/public support acknowledgement are visible, empty
Send is disabled and server ride/ticket state remains unchanged. Core journeys
are being verified separately; the build alone does not accept them.
The separate nginx delta is web-only and
is not deployed. Live web v8's compiled assets remain independently frozen.

**Reason for replacement:** the [broader v15 native review](../redesign/board-alpha-evidence/native-v15-history-refresh-rejection-20261020.json)
confirms a successful selected-ride/receipt HTTP read followed by loss of the
selected detail. V15 retained no history navigation identifier between refreshed
projections. Preserve v15 and its successful core-trip
records; they do not accept this defect. Native correction proceeds independently
of Railway's continuing new-build pause. The prepared web redirect packet remains
undeployed.

**Earlier v15 core journey and scoped presentation review pass. A
web redirect correction remains prepared but undeployed during Railway's build pause.** The [integrated verification](../redesign/board-alpha-evidence/v15-native-integrated-verification.json)
names the exact passed records and preserves the failed attempts separately.
Both new synthetic Arabic trips use the frozen staging/map-only APKs and confirm
request, private acceptance, pickup, arrival, start, completion, cash pending and
explicit dated cash confirmation. Passenger receipts and independent server
reads agree; the driver finishes offline. The
[same-instance check](../redesign/board-alpha-evidence/v15-same-instance-rebooking.json)
confirms new map selection and a second completed trip in the same passenger
process, closing the retained callback defect without restarting the app.

The [controlled reconnect](../redesign/board-alpha-evidence/v15-native-controlled-reconnect.json)
shows a clear Arabic network error during a 14-second emulator radio interruption.
The server remains `IN_PROGRESS` during and after restoration; no business input
is sent during the outage, and native completion/cash subsequently pass. This is
a bounded synthetic check, not physical field continuity or unknown-outcome
command recovery. [Railway command traces](../redesign/board-alpha-evidence/v15-native-second-http.json)
independently corroborate the second native lifecycle and settlement.

[Native v15](../redesign/board-alpha-evidence/candidate-native-v15.json) remains frozen
with 358 fresh JVM / 291 fresh Android-host checks. Web v8 remains independently
frozen with its hosted applicant/reviewer and representative operations evidence.
The [actual presentation review](../redesign/board-alpha-evidence/v15-native-presentation-review.json)
now covers eight role/style checks, both Notepad restarts, both 1.3× font checks,
fresh French/English account/receipt/earnings renders and five named native Tab
stops per role. It does not accept full TalkBack, every financial row or all pages.
[Fresh hosted readback](../redesign/board-alpha-evidence/v8-final-board-readback-20261020.json)
confirms normal MFA, Casablanca recruitment and matching staff/applicant submitted
revision 7 without a new review decision or submission. Current live v8 still
passes [all 102 existing hosted checks](../redesign/board-alpha-evidence/hosted-web-v8-20261018-oct20-final-current.json).

The final browser pass exposes `/apply` redirecting to internal HTTP port 8080.
The [new redirect check is red](../redesign/board-alpha-evidence/hosted-web-v8-proxy-r1-20261020-red.json).
The [proxy-only packet](../redesign/board-alpha-evidence/candidate-web-v8-proxy-r1.json)
keeps all 93 compiled v8 assets unchanged and makes redirects relative. Eight
packaging checks pass, but Railway rejects upload with a temporary platform build
pause. [The pause record](../redesign/board-alpha-evidence/web-v8-proxy-r1-deployment-pause.json)
confirms no new deployment. The canonical HTTPS `/apply/` portal works. The next
required step is deploy → 103 hosted checks → normal `/apply` browser entry once
Railway resumes builds; do not buy an upgrade or evade the pause.

Use [the concise handoff](../board-alpha-handoff.md) for exact artifacts, current
limits and continuation. Its current ten-gate index records **0/10 formal owner
acceptances** separately from the substantial verified engineering evidence;
remaining broader visual/failure/device/accessibility and timed-rehearsal scope
is not reduced to the pending redirect deployment. Physical Android remains deferred; iOS, all 213 views,
approved place search, real transport/money and public launch are not accepted by
these results. Arabic app UI/RTL is available; Valhalla narration uses English
fallback. Four extra Casablanca roles expired at 11:27 UTC under the owner's
24-hour approval; baseline recruitment access remains and no renewal is implied.
Both owned headless emulators were shut down normally after native verification,
with app data retained and font settings restored. Hosting stays trial-only.

## Diagnostic and build history — 20 October 2026

**Board acceptance remains pending.** V13's Android request-priority repair passes
native overlap/recovery verification, but the same passenger map fails destination
selection after completing a trip. The
[same-APK idle restart diagnostic](../redesign/board-alpha-evidence/v13-map-idle-restart-diagnostic-20261020.json)
then succeeds without a new booking. The
[failure record](../redesign/board-alpha-evidence/native-v13-post-trip-map-rejection-20261020.json)
preserves both outcomes and exact pinned-library bytecode evidence: MapLibre
retains the initial click callback, which captures the old active-trip state.
The bounded repair binds retained native listeners to the latest Compose callback
for Android/iOS. Two focused regressions cover active→idle selection and idle→active
guard preservation. Both checks [fail with the original binding semantics](../redesign/board-alpha-evidence/map-callback-red-20261020.json)
and [pass with the stable current-callback adapter](../redesign/board-alpha-evidence/map-callback-green-20261020.json).
V14's [412 source inputs](../redesign/board-alpha-evidence/native-v14-build-inputs.json)
are frozen with exactly four changes from v13: shared adapter, Android/iOS wiring
and the two-test JVM regression. The
[v14 candidate](../redesign/board-alpha-evidence/candidate-native-v14.json) now passes
358 fresh JVM / 291 fresh Android-host checks and actual staging/map-only APK
configuration verification. The full build completed in 3m34s with build cache
disabled for test freshness. Actual replacement runtime acceptance remains pending.
The source audit now covers 268 declarations / 59 files; the
213 views remain an inventory, not accepted native pages.

The installed v14 map accepts initial destination selection and enables fare
review. Its actual recent-destination list exposes long coordinate strings;
[the visual preflight](../redesign/board-alpha-evidence/native-v14-display-polish-preflight-20261020.json)
preserves that render before any booking. The bounded v15 presentation packet
shortens this fallback to at most five decimals while selecting the original
full-precision point. Its [412 inputs](../redesign/board-alpha-evidence/native-v15-build-inputs.json)
differ from v14 in one passenger UI file. The
[v15 candidate](../redesign/board-alpha-evidence/candidate-native-v15.json) passes
358 fresh JVM / 291 fresh Android-host checks and actual staging/map-only APK
configuration checks; the full build completed in 4m56s with test build cache
disabled. Actual two-trip/visual acceptance remains pending; neither preparation-only record is a
complete native rehearsal. No additional feature or backend-policy change is
included in this display correction.

Next: prove both callback transitions, freeze the replacement, then perform two
complete native journeys with same-instance post-trip rebooking. Finish actual
four-style account/receipt/earnings, larger-text, restart and core accessibility
review before the final handoff. No restart workaround or old-version trip counts
as completion of these requirements. Live web v8 remains independently frozen;
all five staging services are online at the 20 October 09:13 UTC check.
The four extra Casablanca staff roles expire today around 11:27 UTC under the
owner's 24-hour approval; no renewal is implied. Physical Android remains deferred.

## Historical standing — 19 October 2026

**Implementation is advancing; board alpha is not yet accepted.** Web v8 is now
live at `ceee310c-e957-49ad-945d-b9f2d292eb61`, with
[102 hosted checks](../redesign/board-alpha-evidence/hosted-web-v8-20261018-oct19-first.json)
passing against 93 exact assets. The preserved Omar applicant draft now passes
[actual UI Save and Submit](../redesign/board-alpha-evidence/v8-applicant-save-submit-20261019.json):
revision 1 → saved revision 2 → submitted revision 3, independently confirmed by
an owned server read. This closes the observed v7 Save failure for that path.
The [matched review/correction loop](../redesign/board-alpha-evidence/v8-matched-review-correction-20261019.json)
also passes through revision 7, including explicit expired-session recovery and
deliberate resubmission. Broader visual acceptance remains separate.

The owner-approved [staging staff setup](../redesign/board-alpha-evidence/scoped-demo-access-verified-20261019.json)
is applied: three synthetic MFA platform administrators have non-expiring
bootstrap grants; four additional Casablanca reviewer roles expire on 20 October
at 11:27 UTC. Existing reviewer grants are preserved. Protected HTTP maker-checker
requests and distinct synthetic requester/reviewer accounts created the city
grants. This tests the mechanism, not independent human governance. No production
or real-money command is included. [Native v11](../redesign/board-alpha-evidence/candidate-native-v11.json)
is frozen with verified staging/map-only APKs and 353 fresh JVM / 291 Android-host
tests. Its two required trips remain open. The first build failed one stale
cash-copy assertion; its archived failure and test-only correction are preserved.
The [first actual v11 trip is rejected](../redesign/board-alpha-evidence/native-v11-runtime-rejection-20261019.json):
booking, private acceptance and transitions through `IN_PROGRESS` pass, but native
completion-coordinate acquisition fails. Normal retries and a bounded offline
diagnostic do not recover it; original emulator network settings are restored.
Ride `359279df-4847-4ad3-bfa4-baa2136b45be` was preserved in progress for the
corrective build. It is now [recovered through the v12 native UI](../redesign/board-alpha-evidence/v12-native-preserved-trip-recovery-verified.json):
fresh completion coordinate, exact ride completion, 35.00 MAD cash-pending review,
explicit cash confirmation, passenger/server cash-completed state and driver
offline readback all pass. This partial old-ride recovery never counts as either
of the two required new-candidate rehearsals. The first v12 attempt was blocked
before lookup by a bundled System UI boot ANR. The successful second attempt's
final cleanup expected a redundant Go offline control; a separate readback
confirms the driver was already offline. Both failed helper records are preserved.
Three focused checks
reproduce the old completion behavior. The source correction now uses the guarded
driver-observation callback and actionable retry copy when manual fields are
disabled. Its [focused red/green record](../redesign/board-alpha-evidence/completion-observation-green-20261019.json)
now passes all three checks. The first two green attempts exposed test selectors
that ignored the existing spinner semantics; their failed records are preserved.
V12's [411 inputs](../redesign/board-alpha-evidence/native-v12-build-inputs.json) are
frozen, with exactly three native UI/test source changes from v11. The
[v12 candidate](../redesign/board-alpha-evidence/candidate-native-v12.json) now passes
355 fresh JVM / 291 Android-host tests and both actual staging/map-only APK
configuration checks. The [first clean French rehearsal](../redesign/board-alpha-evidence/v12-native-first.json)
now passes on these exact APKs: native booking/private acceptance, all trip
transitions, fresh completion, cash-pending review, explicit dated amount
confirmation and passenger/server cash-completed readback. Ride
`d699a0f9-44fc-44d3-9036-56aedd8c10b9`, 35.00 synthetic MAD; 19:33–19:38 UTC.
The second clean full rehearsal remains pending. The
[Arabic attempt](../redesign/board-alpha-evidence/v12-native-second.json) reaches
`IN_PROGRESS`, but the completion-location lookup returns unavailable and keeps
completion disabled. The visible Arabic retry is actionable; its native
continuation also fails lookup. The
[runtime failure checkpoint](../redesign/board-alpha-evidence/native-v12-arabic-runtime-failure-20261019.json)
preserves the same in-progress ride. Source review identifies an Android ownership
gap: automatic sampling can occupy the shared native slot while the explicit
lookup button appears available. The exact cause of each failure is uninstrumented.
The bounded v13 repair uses the existing one-shot gate to prioritize the first
explicit lookup, suppress preempted automatic cancellation warnings and defer
sampling until the callback. Foreground/context/freshness validation is retained.
[21 focused checks](../redesign/board-alpha-evidence/driver-explicit-location-priority-focused-20261019.json)
pass; they do not claim an Android platform race reproduction. V13's
[411 inputs](../redesign/board-alpha-evidence/native-v13-build-inputs.json) are frozen
with exactly two changed files from v12. The [v13 candidate](../redesign/board-alpha-evidence/candidate-native-v13.json)
now passes 356 fresh JVM / 291 fresh Android-host checks and actual APK staging/
map-only configuration verification. The first compiled build's cached Android
test reports were [rejected by the freshness check](../redesign/board-alpha-evidence/native-v13-first-build-freshness-rejection.json);
the same sources were revalidated with the build cache disabled. No source change
or old test timestamp was waived. Runtime acceptance remains pending.
Preserve both failed Arabic records and recover the same trip
only through the replacement app. Do not infer a completed Arabic journey.
Both exact v13 APKs are installed with app data retained. The first recovery
attempt was blocked before location lookup by bundled launcher/System UI boot
ANRs. Their observed Wait/Close app actions and screenshots are preserved; no
TaxiMobile data reset, security-setting change or physical-device action occurred.
This system-dialog interruption does not test or reject the v13 ownership repair.
The [actual v13 priority/recovery verification](../redesign/board-alpha-evidence/v13-native-priority-and-preserved-recovery-verified.json)
now passes its bounded scope. Android's trace shows automatic request `84E2F093`
removed without a delivered fix, immediately followed by explicit request
`EFF7C851` receiving a fresh fix. The second recovery helper's automated Complete
tap did not produce an API proxy request. After independent `IN_PROGRESS` and
fresh enabled-control review, one explicit native click completed that same ride;
the API trace contains its single successful request. Native Arabic dated cash
confirmation, passenger/server cash-completed state and driver offline readback
then pass. Failed helper records remain unchanged. This is recovery of an old
v12 trip, not either required new v13 rehearsal. The two new rehearsals are being
stepped through actual fresh screenshots with per-command state/readback records;
no consequential command is automatically replayed.
The earlier
[first French v12 attempt](../redesign/board-alpha-evidence/v12-first-attempt-20261019T193301722760Z.json)
reached pickup but did not confirm Start. A single explicit native retry after
independent pickup readback started the same trip. Its
[recovery readback](../redesign/board-alpha-evidence/v12-native-first-fr-trip-recovery-verified.json)
confirms native completion, pending/confirmed cash, passenger confirmation and
offline driver state. The recovery helper's last accessibility read failed;
its failed record remains separate. Neither recovery counts as a clean full run.
The initial missed Start action has no established cause. Live web v8 retains
its own exact inputs and assets; this native
repair changes no resources, dependencies, wire contracts or backend authority.
This qualifies the build and configuration, not native runtime acceptance.
Do not relax freshness, enable hidden manual input or complete it directly by API.
The [Arabic support claim](../redesign/board-alpha-evidence/v8-support-participant-privacy-20261019.json)
passes with separately labelled participant/internal notes; participant readback
includes only the public acknowledgement and excludes internal/staff fields.
The [support/booking visual record](../redesign/board-alpha-evidence/v8-support-booking-visual-review-20261019.json)
also shows the same expanded booking economics/refund cutoff across AR/FR/EN and
Glazed Machine→Notepad. The separate
[payment empty-state review](../redesign/board-alpha-evidence/v8-payments-empty-state-review-20261019.json)
passes EN/FR/AR guidance and scope retention in Notepad/Street Press. No populated
reconciliation, recipient activation or financial command is accepted by that check.

The passed
native trip uses [v9](../redesign/board-alpha-evidence/candidate-native-v9.json).
[Native v10](../redesign/board-alpha-evidence/candidate-native-v10.json) is an archived
intermediate surface build, with verified APK configuration and 348 JVM / 289
Android-host tests; it has no trip acceptance. The separate
[historical web v7](../redesign/board-alpha-evidence/candidate-web-v7.json) passes 71
fresh browser tests, eight packaging tests and all 102 hosted checks. Five Railway
services are online. Its protected recruitment/applicant review has
[actual EN/FR/AR evidence](../redesign/board-alpha-evidence/wl3-hosted-v7-protected-review.json),
including retained Arabic drafts across four styles. This is partial acceptance:
protected writes, contrast defects and remaining board operations stay open.
Earlier v6 password/MFA recovery and selected-city retention remain historical
evidence. Twelve earlier actual Android
welcome style/language renders, one complete v6 native cash trip, an earlier
native cash trip and v5's server-confirmed old-cash recovery are evidenced below.
V9's actual APK configuration passes the staging/map-only gate, and one complete
native cash trip now passes. V8 is rejected because its APKs target the local API and enable
place search, contrary to its original manifest. These are distinct checks.

Current critical path: verify the v13 repair, recover the preserved Arabic ride,
finish representative board operations in EN/FR/AR and run the final frozen
native journey twice. Shared web resources
also change native APK identity; intermediate builds do not each need two complete
trips. Finish the seven-beat presentation checks on that final freeze. V6 private acceptance,
cash authority and corrected compact no-supply recovery now have actual emulator
evidence below; one v6 trip is not two complete board rehearsals.
Protected-web FR/AR/RTL, complete core visual/accessibility review and final
handoff remain required. Physical Android is deferred by the owner; its gates
stay open. The chronological evidence below must not be read as blanket gate
acceptance or acceptance of all 213 views.

### Fresh checkpoint — 18 October 2026

Web v7 is live as `7e30999d-719b-4f84-bda0-8bf45baccc2a`.
[All 102 hosted checks](../redesign/board-alpha-evidence/hosted-web-v7-20261018-client-headers.json)
pass, including 93 exact assets, applicant routing, security headers and version/auth
boundaries. The first probe omitted client metadata and received the correct 426;
its failed record is preserved. The 21m59s optimized build and 71 fresh tests pass.

Nineteen actual JPEG captures document scoped Arabic recruitment/review, privacy
suppression, requirement/evidence labels, RTL queue actions, a retained Arabic
unsent message in French and all four styles, and a submitted applicant across
FR/AR/EN. Arabic withdrawal review was opened and cancelled; no review decision,
withdrawal or eligibility change was submitted. This is not a complete style/locale
matrix or write-flow acceptance.

The [post-v7 source checkpoint](../redesign/board-alpha-evidence/wl4-overview-polish-source-20261018.json)
corrects the observed dark applicant-header refresh contrast, dense ISO queue dates,
ride-specific style copy and English MFA reverify-success notice, and translates
the read-only rollout overview. JS/Wasm compilation, 72 browser tests and 988-key
EN/FR/AR catalog validation pass. These changes are not deployed in v7.

The subsequent editable rehearsal created a complete profile-only Casablanca
draft, but **Save draft failed**. The client omitted empty answer/evidence arrays;
the backend correctly rejected the resulting version-only PATCH with 422. The
[failure record](../redesign/board-alpha-evidence/wl3-v7-editable-contract-failure.json)
preserves the unchanged `NOT_STARTED` revision 1 and actual screenshots. Keep this
draft for the corrected UI retest; no submission or review decision was made.
The [source transport fix](../redesign/board-alpha-evidence/recruitment-wire-source-fix-20261018.json)
now passes a reproduced red/green HTTP serialization regression (three focused
tests) and eight backend recruitment unit tests. It preserves explicit empty
patches, removal IDs and conflict handling. The actual replacement-UI save remains
required; v7 still contains the defect.
Editable applicant/requirements writes, protected documents, WL-4 operations,
full accessibility/responsive checks and final native repeats remain required.
The subsequent [payment source checkpoint](../redesign/board-alpha-evidence/wl4-payments-source-20261018.json)
passes JS/Wasm compilation and 73 browser tests in 6m50s, with 1,063 validated
EN/FR/AR keys. Payment forms and feedback are translated; status/action labels
are display-only and money/reference/date values retain direction. No new
package is deployed and no financial command or payment UI acceptance is
inferred. Support/trip presentation and final runtime rehearsals remain open.
The trial review is 14 days / $3.26 at its timestamp; both volumes remain preserved.

The subsequent [case/booking source packet](../redesign/board-alpha-evidence/wl4-cases-bookings-source-20261018.json)
passes JS/Wasm compilation, 75 browser tests and 1,218-key EN/FR/AR validation.
Support/safety/retention dialogs and feedback plus scoped booking/linked-trip
display are translated without changing commands or visibility. Known refund
terms follow their snapshotted policy; unknown policies stay unavailable.
[411 exact inputs](../redesign/board-alpha-evidence/web-v8-build-inputs.json) are now
frozen for the optimized v8 replacement. V8 is not yet packaged/deployed or
accepted. The [runtime preflight](../redesign/board-alpha-evidence/railway-pre-web-v8-runtime-20261018.json)
shows five online replicas, no reported issues and no pending Railway work.
Actual case/booking/payment review, corrected Save/Submit, final paired candidate
and two native rehearsals remain required.

During v8 optimization, the [temporary bootstrap configuration cleanup](../redesign/board-alpha-evidence/api-bootstrap-cleanup-20261018.json)
removed only the four one-time API seed inputs and redeployed the existing normal
migration build once. API `e5e108a0-e5dd-4553-93fd-292026c98b63` is successful;
five replicas are online. Readiness, owner login/read and proxy boundaries pass,
and Omar's preserved failed-save draft is still `NOT_STARTED`, revision 1.
No seed reset, credential rotation, schema advance or new UI acceptance occurred.

### Earlier checkpoint — 17 October 2026

The combined surface build completed in 14m22s with 348 JVM, 289 Android-host and
67 browser tests passing. All 406 captured inputs match its immutable archive;
both APKs pass direct staging/map-only configuration inspection and differ from
v9. Native v10 remains intermediate because the reviewed shared confirmation
contrast/shape defect is not fixed in those APKs.

Web v6 was deployed as `72a8722f-c230-4de3-9126-cd9d72ec1d29`, with 93 assets /
28,611,904 source bytes. [All hosted checks](../redesign/board-alpha-evidence/hosted-web-v6-20261017.json)
pass. [Actual runtime proof](../redesign/board-alpha-evidence/wl2-hosted-v6-session-recovery.json)
verifies grayscale Notepad, reachable MFA retry/cancel, fresh French/English MFA
and Casablanca retained across EN/FR/AR. Protected body translation, bidi counts,
desktop card bounds and accessibility remain open.

Post-v10 source now fixes confirmation action colors/shapes and shortens cash
copy in all three languages. [Three focused JVM tests](../redesign/board-alpha-evidence/confirmation-source-fix-20261017.json)
and the 730-key localization check pass; no newer APK contains this fix yet.
Operations entry/MFA width modifiers are also corrected in source after the
desktop runtime showed their intended maximum width was ineffective. A new
web build and actual bounded-card render are required.

Direct Android SDK inspection of all six archived v6/v7/v8 APKs found correct
staging/map-only configuration in v6/v7 and incorrect local-API/place-search
configuration in v8. Preserve the original manifests and read the
[artifact audit](../redesign/board-alpha-evidence/native-configuration-audit-20261017.json)
as the correction to v8's hard-coded configuration claim. No v8 trip passed.

V9 rebuilt the presentation source with explicit staging/map-only flags. Both
APKs and 403 source inputs are archived. The
[actual APK configuration record](../redesign/board-alpha-evidence/native-v9-configuration.json)
and candidate manifest record values read from APK bytecode, not inferred from
build arguments. The repository's `scripts/validate_board_apks.py` rejects v8
and passes v9; candidate packaging now requires that check. V9's native tests
pass 347 JVM / 288 Android-host checks. Both APKs installed on AOSP API 31;
passenger sign-in passed and the driver restored an authenticated session.
Vulkan is required by this MapLibre renderer. With Vulkan enabled both maps render.
API 31 GPS fixes report epoch-sized elapsed timestamps against an hours-long boot
uptime and are correctly rejected by fresh-acquisition policy. This fixture cannot
establish trip acceptance. Preserve the failed v9 attempts; use a valid newer
driver fixture without weakening native freshness or server dispatch rules.

The [clean API 35 driver fixture](../redesign/board-alpha-evidence/v9-clean-api35-location-fixture.json)
now passes actual sign-in and fresh location acquisition. With that driver and
the API 31 passenger, [the first v9 trip](../redesign/board-alpha-evidence/v9-native-first.json)
passes exact installed hashes, native on-demand availability, booking, private
acceptance, all trip transitions, completion and cash pending-to-confirmed receipt.
The synthetic fare is 35.00 MAD. The [actual passenger receipt](../redesign/board-alpha-evidence/v9-first-cash-completed.png)
matches server-confirmed settlement. This is one v9 run; the newer surface/MFA
source corrections need new candidates and final repeat evidence.

The [actual cash-dialog review](../redesign/board-alpha-evidence/v9-cash-dialog-contrast-review.json)
confirms its fare/date context but rejects action-label contrast. Shared
`ConfirmDialog` still uses dark ink on the primary action and omits an explicit
style button shape. Correct it with the existing on-primary/on-error roles and
selected radii before the final native freeze. The in-flight surface v10 build
does not include this newly identified correction. A passed lifecycle is not
visual or accessibility acceptance.

The [local web record](../redesign/board-alpha-evidence/wl2-local-browser.json)
separates earlier entry renders from the final corrected bundle. The actual
English form now renders French accented and Arabic characters together.
Responsive draft retention and Arabic validation passed. The preview refused
a protected `/me` read during v8 diagnosis; it supplied no session or write
success. Earlier web v5 deployed as `62985a05-46c3-4b74-8bcd-d101f003e18b`.
All 93 packaged assets and five anonymous boundaries pass (98 checks), following
67 browser tests and eight packaging tests. Fresh hosted password/MFA sign-in
passed in French; switching to Arabic retained the authenticated Morocco scope
and applied RTL. The [hosted scope record](../redesign/board-alpha-evidence/wl2-hosted-v5-session-scope.json)
also verifies explicit Casablanca selection retained across Arabic, English and
French. Protected body copy remains partly English; full protected translation
and accessibility checks remain open. The deployed Notepad dialog inherits a
lavender Material surface, and an MFA error can clip cancel in a short viewport.
Source corrections map the remaining Material surface roles and make MFA content
scrollable; they are not in v5 or the frozen native v9 APKs. The
[focused source record](../redesign/board-alpha-evidence/wl2-surface-scroll-source-fix.json)
passes two JVM color/contrast regressions and shared JVM compilation. Web compilation
and actual corrected short-height/dialog renders remain required.

The [17 October Railway capture](../redesign/board-alpha-evidence/railway-trial-20261017.png)
shows 15 days or $4.05 remaining. All five services are online, with no issues
or pending changes. Latest PostGIS samples are approximately 0.233 GB disk and
0.234 GB memory. Review allowance again on 18 October or before sustained work;
keep the trial-only constraint and both preserved/active volumes.

At the [09:09 UTC service check](../redesign/board-alpha-evidence/railway-status-20261017T0909Z.json),
all five services remain online without issues, recent failures or pending work.
PostGIS's latest one-hour samples are 0.223 GB disk / 0.336 GB memory. These newer
resource samples do not refresh the earlier billing allowance screenshot.

### Build and local-render checkpoint — 16 October 2026

V7's complete native/test plus JS/Wasm source and JS development build succeeded
in 17m49s. Its APKs and 401 source inputs remain archived. V8 retains its online
acquisition guard and makes Notepad map controls square and flat. The combined
v8/WL-2 build passed 347 JVM, 288 Android-host and 67 browser tests, both APKs,
JS/Wasm source compilation and JS development packaging. V8's APKs and 403 source
inputs are archived with matching hashes. Subsequent web-only font refinements
belong to the separate web candidate.

V8 installed successfully on both owned API-35 emulators. Cold startup produced
Pixel Launcher/System UI ANRs; captures are preserved. Android increased each
requested 1536 MB guest to 2560 MB, so the fixture must not be described as two
1536 MB guests. No v8 trip is counted. The driver was server-confirmed offline
and no active ride existed before this attempt. Physical-device checks remain
deferred under the owner's instruction to continue with the emulator.

Actual local web checks verify French resource changes, Arabic RTL, retention of
an unsent login draft across language changes, and Arabic persistence after
reload. Recorded requests contain public compatibility/catalog GETs only. They do not
establish authenticated scope retention or complete web translation. The Arabic
option font correction passed its actual French/Arabic render. WL-2 now translates
the entry/MFA/shell and adds the existing abstract strip. Actual applicant checks
cover Arabic/French entry, Notepad English entry, Arabic narrow registration and
localized validation. A desktop-breakpoint draft-loss bug is repaired and actual
390-to-1280 dp retention passed. Arabic names still showed missing glyphs in an
English form; that web-only correction passed an actual render on 17 October. Authenticated web
session/scope checks and the remaining protected view translations remain open.
Protected web remains v4 in staging.

The [current Railway trial capture](../redesign/board-alpha-evidence/railway-trial-20261016.png)
shows 15 days or $4.17 remaining. All five services are online with no issues or
pending changes; the ten hosted boundary/hash checks pass again. PostGIS metrics
show approximately 0.263 GB disk and 0.181 GB memory. These are time-specific
observations, not ongoing credit or capacity guarantees. Keep the trial-only
constraint and preserved original volume; review usage on 17 October or before
additional sustained rehearsal.

## Owner instruction — 15 October 2026

Deliver the earliest functional board presentation alpha. The owner authorizes
implementation of the selected identity and changes/deployment within TaxiMobile's
Railway staging project. This supersedes the earlier planning-only stop. Preserve
unrelated projects and existing data. Keep French, Arabic and English available,
shorten nonessential copy, and preserve explicit fares, payment states and recovery.

## Next demonstrable outcome

The [18 October WL-3 source checkpoint](../redesign/board-alpha-evidence/wl3-protected-source-20261018.json)
covers recruitment requirements/review/authorization and the protected applicant
dashboard/editor/documents/withdrawal, including localized feedback. JS/Wasm
compilation, 71 browser tests and 950-key catalog validation pass. The optimized
[v7 candidate](../redesign/board-alpha-evidence/candidate-web-v7.json) is now frozen:
71 fresh browser tests, eight packaging tests, 93 assets / 29,060,729 raw bytes.
It is deployed and all 102 hosted checks pass; the scoped protected runtime
record above defines the actual UI verification boundary.
Actual protected EN/FR/AR renders and flow rehearsal remain required. No partial
packet was published; web v7 is the current hosted candidate. The remaining
shared reverify-success notice must be translated before full web-language acceptance.

The [18 October Railway review](../redesign/board-alpha-evidence/railway-status-20261018.json)
confirms five successful services and no pending work. The trial banner shows
14 days / $3.26 remaining; PostGIS uses 0.224 GB disk / 0.290 GB memory. Preserve
both volumes and trial-only limits; review again before sustained hosted rehearsal.

One coherent staging candidate: passenger and driver Android builds, operations
and applicant web, real backend ride/cash lifecycle using synthetic accounts.
Folded Streets, Street Press, Glazed Machine and Notepad are the only style choices.
No main city/taxi hero and no separate color menu. Reuse the selected abstract
geometry, typography and tokens. Keep task controls stable. Notepad retains icons
and the full main workflows in grayscale with decorative animation disabled.

| Order | Work | Exit evidence |
| --- | --- | --- |
| 1 | Reconcile current dirty source and live staging; establish candidate manifests | Preserved source baseline and exact project/environment; current failures recorded |
| 2 | Shared style preference, fonts, colors, shapes, components and abstract entry frame | All four styles in actual app; persistence and draft/state retention tests; FR/AR/EN renders |
| 3 | Passenger/driver journey polish and concise navigation | Welcome/auth, map selection, fare, request, private offer, assignment, trip progression, cash pending and confirmation; recovery remains actionable |
| 4 | Repair and deploy Railway web/API/worker/routing as needed | HTTPS entry, protected operations/applicant sessions, DB-backed readiness and complete synthetic lifecycle |
| 5 | Rehearse and package | Exact APK/web/backend hashes, screenshots, short board script, twice-run outcome and honest provider/device disclosures |

Steps 2–4 may overlap when builds/provider operations leave independent work
available. Finish one working slice before expanding optional functionality.
All 213 documented views remain the rollout inventory; the board's critical path
prioritizes current core journeys over deferred capabilities. A passed source or
browser check does not mark every native view accepted.

## Boundaries and acceptance

Keep KMP/Compose, FastAPI/PostGIS and server-owned identity, eligibility, pricing,
assignment and payment. Map selection is the alpha location flow; place search
remains unavailable until an approved provider exists. Use synthetic people,
documents, trips and money. Production/pilot activation remains a separate decision.

The existing TaxiMobile Alpha project is the staging target. Reuse its database
and private API/worker/routing boundaries; repair the failed web service. Do not
remove volumes or unrelated projects to obtain a successful build. Record ongoing
resource exposure and actual account availability when accessible. No billing-plan
upgrade is implied by this work.

Status and evidence are appended below as implementation progresses. No board
readiness claim is made until the actual integrated journey has been verified.

## Implementation status

15 October baseline: current Railway inventory has API/worker/routing deployments
marked successful, PostGIS with its existing volume, and a failed alpha-web
deployment. Current source still has the old static navy/gold theme and main
welcome illustration. Shared style implementation and fresh staging verification
are in progress.

### Verified checkpoint — 15 October 2026

The baseline above is historical. Shared style selection is now implemented in
the application: immutable per-style palettes, Plex/Arabic/Jakarta typography,
geometry, component colors, persistent local preference and bounded abstract
welcome motion. Notepad uses grayscale semantic states, square controls, static
rules and no decorative animation. Selection keeps the current form and sends
no domain command. Android, JVM, JavaScript and Wasm compiled; iOS has a platform
preference implementation but has not been compiled or rehearsed on this host.

The first green candidate passed 331 JVM and 276 Android-host tests, built both
staging-targeted debug APKs and the JS/Wasm compatibility distribution. Actual
Android emulator renders cover all four styles in English, French and Arabic;
Notepad persisted across a process restart. These twelve welcome checks do not
accept every application page. Final polish adds an RTL margin correction,
selected-action contrast fixes, a shorter active driver panel and removal of
manual completion coordinates when the staging diagnostic-entry flag is off.
The final rebuild and repeat rehearsal remain required for those changes.

Two hosted REST rehearsals each passed 21 checks, including server matching,
cash pending/confirmation, wrong-role denial and idempotency. Separately, the
first integrated Android rehearsal on two API 35 emulators created ride
`59576371-85a9-4732-a100-12f7295f0c0a` using map-selected points and a 35.00 MAD
server fare. The driver accepted the private offer and progressed through
heading/arrival/start/completion. The passenger's actual receipt showed
`Cash · Pending`, then `Cash · Completed` only after the driver's dated cash
confirmation dialog. Accounts, GPS fixes, payment and trip are synthetic.
This was one native pass on the pre-polish candidate, not the twice-run final
board rehearsal. A single emulator missed a prior offer while the driver was
backgrounded; use two active role instances for the integrated demonstration.

Operations web password plus authenticator sign-in, Casablanca scope, recruitment
queue and pending application review were inspected at compact and desktop
widths. No applicant eligibility decision was changed during this inspection.
The operations/applicant interface still contains English-only copy and needs
its own complete FR/AR/RTL rollout before claiming a fully trilingual web demo.
The browser session returns to sign-in after reload. Do not promise unattended
session restoration or treat a successful MFA challenge as full console acceptance.

### Railway recovery and boundaries

All five staging services are online. The original full 500 MB volume
`alpha-postgis-data` is preserved unattached. The owner applied the approved
trial-only swap to fresh 500 MB `alpha-board-data-20261015`; no paid plan or
volume deletion occurred. Fresh PostGIS migration, constrained runtime role,
synthetic cohort and operations MFA bootstrap succeeded. The latest API upload
uses normal `migrate` pre-deploy, avoiding a repeat seed on ordinary redeployment.
Web Nginx now resolves the private API at runtime using the container DNS
resolver with IPv4 upstream selection. HTTPS proxy access was verified after
the API redeployment. See [deployment.md](../deployment.md) for IDs and limits.

### Next bounded packets

1. Finish the current surface/MFA build, verify actual APK configuration and source
   hashes, deploy the curated web output and check corrected native/web renders.
2. Complete [the bounded protected-web localization packet](../redesign/web-localization.md)
   for concise operations/applicant FR/AR resources and RTL layout, then
   rehearse the representative protected web journeys in all three languages.
3. Freeze native and web after the shared presentation resources settle. Repeat
   the complete two-emulator trip twice on that exact final candidate, including
   restart, reconnection and clear network fallback. Record elapsed interactions;
   do not spend the two-run acceptance on each intermediate shared-resource build.
4. Review actual core-page screenshots in every style; distinguish shared token
   coverage from acceptance of the 213-view inventory. Finish map/style and
   accessibility checks, including large text, focus and reduced motion.
5. Physical Android is deferred at the owner's request to continue with emulators.
   Keep AG-05/AG-08 physical evidence open; no pilot/public acceptance follows.
6. Package the final seven-beat script, exact candidate manifest and honest
   provider/cost/reset disclosures. Preserve synthetic records and the old volume.

Use [the seven-beat rehearsal draft](../board-demo.md) for the room sequence,
EN/FR/AR narration and stop rules. Its final-candidate acceptance remains open.

### Refined candidate built and deployed — 15 October, 16:22 UTC

The complete refinement build passed in 14m 28s: **332 JVM** and **276
Android-host** tests, zero failures/errors/skips, both Android role debug APKs,
and the JS/Wasm compatibility distribution. This includes the RTL margin,
selected-action contrast and active-driver/completion-field improvements.
[Candidate identity](../redesign/board-alpha-evidence/candidate.json) records the
two exact APK hashes, 394 source-input hashes, configuration and limitations.

Web deployment `53c3708b-fd08-4e92-8fc3-32de472c43a2` is online. Ten fresh
[hosted release checks](../redesign/board-alpha-evidence/hosted-polish-release.json)
passed: private API compatibility proxy, anonymous ride denial, health,
manifest/source-map denial, and exact HTML/JS/Wasm asset hashes. The curated
package has 92 assets / 28,234,256 source bytes with maps excluded. Android
installation and the repeat native journey are now the next checks on this
exact candidate. The earlier native cash trip remains pre-refinement evidence.
Browser Notepad selection persisted after reload and retained Casablanca scope
and the active session during the style switch itself; reload returns to login.
Full board, web-language, per-view and physical gates remain open.

### Native repeat failure and corrective packet

The refined repeat created ride `03756c30-f453-4d09-ae50-c3fa8f3782a4`, but the
private acceptance was missed and the server ultimately marked it UNMATCHED.
The driver was server-confirmed AVAILABLE / ON_DEMAND. The old seeded cash item
also remained pending after a submitted UI interaction; it is not counted as
recovered. No server record was manually edited to repair either result.

Inspection found automatic foreground GPS uploads followed by full dashboard
reloads under the single action gate, repeatedly blocking unrelated controls.
A focused native correction now acknowledges GPS onto the latest confirmed
projection, refreshes only advisory guidance, and fences session/trip-phase
races. Four new regressions cover no dashboard reload, rejection, session change
and newer-phase preservation. Its native build and integrated repeat are pending;
the deployed web candidate and earlier APK hashes remain the last verified
artifacts until a new native candidate is recorded. See the
[driver acknowledgement contract](../drivers.md).

### Native location candidate verified locally and in cash recovery

The correction built successfully in 4m 11s: **336 JVM** and **280 Android-host**
tests, no failures/errors/skips, both role APKs. The source recovery guard and
its six tests pass with the explicit Notepad immediate-success policy; graphic
asset validation passes. [Native candidate v5](../redesign/board-alpha-evidence/candidate-native-v5.json)
preserves exact hashes and archived APK paths. The deployed web remains the
separately identified v4 package; no web behavior or backend API changed here.
iOS wiring is updated in source but remains unbuilt/unrehearsed on Windows.

On v5, actual driver UI GPS submission and on-demand availability were followed
by the dated 13 October / 35.00 MAD synthetic cash dialog. This time the
[server-confirmed recovery](../redesign/board-alpha-evidence/native-v5-location-cash.json)
reduced the queue from one to zero, and the
[native cash item disappeared](../redesign/board-alpha-evidence/native-v5-cash-recovery.png).
The record's 13.93 seconds includes UI discovery/scrolling from location request
to the enabled online action; it is not a raw API latency measurement. A new
private-offer trip and twice-run final rehearsal remain required before closing
the native gates. Do not reinterpret the earlier missed acceptance as passed.

### Next native packet — fresh acquisition and compact retry

The next v5 request (`65f3d974-1cb3-4c43-9486-80cd1007c256`) reached private
acceptance, but the server returned 409 and the ride became UNMATCHED. HTTP
evidence places acceptance about 16 seconds after booking and a rejected GPS
upload immediately beforehand. The generic refusal does not expose its internal
reason; a proposed read-only historical SSH diagnostic could not run because
the CLI has no SSH key. No SSH key or new access was created. Do not label this
as an accepted assignment or assert an unproven precise refusal reason.

Native packet v6 retains the proven location acknowledgement fix and makes
Android wait for a genuinely newer native acquisition within a bounded
15-second foreground request. It preserves server checks and adds cancellation
on foreground exit. It also gives compact no-supply recovery enough sheet space,
uses concise EN/FR/AR previous-request copy, and replaces truncated map-header
names with a short account label while retaining identity for accessibility.
Freshness regressions and whole-action bounds at narrow/large text sizes are
included. The build passed 342 JVM and 284 Android-host tests with no failures,
errors or skips. Both APKs are archived and their exact hashes and 396 source
inputs are frozen in [candidate-native-v6.json](../redesign/board-alpha-evidence/candidate-native-v6.json).
The [actual 360 dp compact retry](../redesign/board-alpha-evidence/v6-no-supply-360dp.png)
shows the complete primary action. The [first v6 trip](../redesign/board-alpha-evidence/v6-native-first.json)
passed native booking, server-confirmed private acceptance, heading, arrival,
start and completion for synthetic ride `d5aab5de-4416-4f4b-bde2-9b424c30a21b`.
The passenger displayed cash pending until the native driver's explicit dated
confirmation, then [cash completed](../redesign/board-alpha-evidence/v6-first-cash-completed.png).
All ride/payment commands used actual Android UI; authenticated HTTP reads
independently checked the resulting state. GPS, identities and 35.00 MAD cash
are synthetic. This is one v6 native trip, not full board acceptance.

Preparation also exposed an emulator GPS fixture initially reporting California,
an expired location at online entry, and an online tap during fresh acquisition.
The failed attempts remain indexed in the evidence directory. Once acquisition
and submission were awaited, both online entry and private acceptance returned
200 without changing backend guards. Gate online interaction during a pending
native acquisition in the next focused UI packet; do not weaken freshness.

### Repeat preparation and language packet — 15 October

The first v6 trip above remains passed. The second repeat is not passed. Failed
attempts include an offline-driver precondition missed by the helper, Android
accessibility timeouts, unmatched requests and a later authentication read
timeout before booking. Their JSON files are preserved separately from the first
successful run. Returning the driver to foreground cleared its connection
warning, but did not by itself establish reliable offer delivery.

Both running emulators were subsequently measured about 57 seconds behind the
host/server clock. Matching requires a recent observation; a fresh monotonic
device fix can still carry a stale device wall-clock timestamp. The test-only
clock correction used `cmd alarm set-time` on the two named emulators, verified
alignment, and changed no server or application provenance guard. The rehearsal
helper now records clock offset and synchronizes before a trip. A complete run
after this correction remains required; do not infer the precise cause of every
earlier unmatched request solely from the clock finding.

Source confirms different windows: `drivers/service.py::location_failure`
accepts uploaded history up to 300 seconds old, whereas matching uses the
configured 30-second dispatch window. An upload acknowledgement alone therefore
does not establish dispatch eligibility. Keep this distinction in the rehearsal
and any future clock-error recovery copy.

The synthetic driver was explicitly returned OFFLINE and both emulators stopped
before building the next source packet. It gates online entry during native
acquisition and implements [WL-1](../redesign/web-localization.md). Native v6 and
hosted web v4 remain the archived/runtime evidence identities until a new build
is frozen and verified. No new web deployment or board acceptance is implied.
