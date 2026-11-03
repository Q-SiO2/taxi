<!-- Historical checkpoint before v22 integrated acceptance; current authority is the active document. -->

# Board alpha — active delivery checkpoint

## Current delivery — 22 October 2026

**V22 layout runtime passes; replacement journeys are pending.** [The manifest](../redesign/board-alpha-evidence/candidate-native-v22.json)
records 414 inputs, exactly four source/test deltas, **389 JVM / 311 Android-host**
passing tests, and both staging-only APK hashes. Six focused checks pass after
four reproduced failures. No failures, errors or skipped tests remain.

[Actual native layout verification](../redesign/board-alpha-evidence/v22-native-map-chrome-verification-20261022-r3.json)
passes on API31 passenger/API35 driver: normal and 1.6 system text, expanded
Inbox access and collapsed shortcut restoration, with twelve saved screenshots.
Both font scales were restored to 1.0. The first observer was interrupted by an
actual Android System UI ANR; its diagnostic is retained. A subsequent observer
had a harness error before UI actions; the separately named successful observer
handles the actual unread-count Inbox label. No app source changed after freeze.

**Current correction: map shortcuts must leave Inbox unobstructed.** Actual v21
fare screenshots expose the floating shortcut stack crossing the toolbar when
the sheet is expanded, in all four styles. The v22 source packet changes only
passenger/driver shortcut visibility/positioning, the shared clearance helper
and its regression tests. Sheet geometry, quote recovery and authentication stay
unchanged. Use the actual font-promoted snap and a 240 dp exposed-map reserve;
collapse restores the stack when room permits. Full replacement acceptance is
pending the frozen build and actual native rehearsal.

V21's [actual new-activity quote verification](../redesign/board-alpha-evidence/v21-native-quote-activity-verification-20261022.json)
passes with enabled Request and unchanged ride list. All four quoted styles pass,
and actual French/Arabic system-language recreation retains the fare and reviewed
points. These are scoped v21 observations; the layout defect withholds presentation
acceptance. No full v21 trip or seven-beat rehearsal was started.

**Retained v21 freeze and scoped runtime:**
[The manifest](../redesign/board-alpha-evidence/candidate-native-v21.json) contains
414 inputs and exactly five reviewed-point/form/test deltas from v20. All
**385 JVM / 311 Android-host** checks pass, without failures/errors/skips. The
[21 focused checks](../redesign/board-alpha-evidence/quote-form-recreation-green-20261022.json)
pass after [five behavior failures](../redesign/board-alpha-evidence/quote-form-recreation-red-20261022.json).
The reviewed point pair is exposed beside freshly authorized terms and seeds
only a new form. Existing local edits keep Request unavailable when they no
longer match the reviewed pair. This is not a general persistent/unreviewed draft
store. Authentication, sheet components, catalogs, API/schema and business command
authority remain unchanged. Both exact APKs install with retained app data and
[authenticated startup](../redesign/board-alpha-evidence/v21-native-retained-startup-20261022.json),
without fresh native sign-in. The replacement must pass the actual new-activity
quote path and two complete journeys/board repetitions before acceptance.

**Retained v20 candidate: full board acceptance withheld.**
Its first replacement journey stops before any booking when a fresh activity
recreates an empty point form. [The preserved rejection](../redesign/board-alpha-evidence/native-v20-quote-activity-recovery-rejection-20261022.json)
and independent readback confirm no new ride, no business command and driver
offline. The coordinator retains the owned quote input, but the fresh composition
cannot associate its empty form with returned terms. The next bounded source
packet projects that existing reviewed input into the passenger render state and
initializes only a newly created form, preserving subsequent local edits. No
cached price, persistent location history or business replay is introduced.

[The immutable freeze](../redesign/board-alpha-evidence/candidate-native-v20.json)
contains 413 inputs and exactly five credential/Android-entry-point deltas from
v19. All **383 JVM / 311 Android-host** tests pass, with no failures/errors/skips.
The [117 focused checks](../redesign/board-alpha-evidence/session-cancellation-green-20261022.json)
include six new cancellation, storage-cleanup and bounded-deadline regressions;
both earlier red attempts are preserved. Android activity and Firebase entry points
now share one application-context credential coordinator per role. Only refresh
and protected commit/cleanup are shielded from caller cancellation, for at most
30 seconds. Backend refresh-family rejection and business command authority stay
unchanged. Test success does not establish the native recovery outcome.

The next packet is exact-v20 repeated activity entry, expired-access recovery,
essential journeys and presentation checks. Preserve passenger app data to observe
its existing refresh family. The driver's already rejected v19 family requires
normal fresh sign-in; that must not be described as recovery of the revoked family.

| Exact-v20 runtime packet | Evidence and status |
| --- | --- |
| Initial retained session / multiple entry | [Bounded progress](../redesign/board-alpha-evidence/v20-native-runtime-progress-20261022.json): passenger restores retained app data without fresh sign-in; passenger plain entries and isolated driver MAIN/LAUNCHER entries reach multiple activity records, same respective process and authenticated UI. Driver plain entries reused one activity; an interleaved locale observer failed and is retained, not counted. |
| Shared sheet / quoted styles | Seven actual header/body observations pass; all four passenger quote styles retain selected locations, 35 MAD backend fare and enabled Request without creating a ride. Exact linked records and hashes are in the progress record. |
| Languages | [Six actual role/language checks](../redesign/board-alpha-evidence/v20-native-localization-verification-20261022.json) pass for EN/FR/AR account and populated receipt/earnings, including Arabic RTL. Initial passenger Arabic observation ran while OS preference still led French; preserved failure and corrected unique r2 are explicit. Both emulators return to English. |
| Welcome presentation | [Eight actual welcome renders](../redesign/board-alpha-evidence/v20-native-welcome-verification-20261022.json) pass across both roles/four styles; both existing accounts re-enter normally. No motion profiling or recovery of an intentionally revoked session is inferred. |
| Passenger account presentation | [Four styles, Notepad restart and 1.3× text](../redesign/board-alpha-evidence/v20-native-passenger-account-style-review.json) pass with unchanged business state. Selected account/financial views only. |
| Controlled driver expiry | [Cold restore](../redesign/board-alpha-evidence/v20-driver-cold-expiry-verification-20261022.json) passes after 966.9 real seconds without the app process, exceeding the 900-second access TTL. Data/session retained, no fresh sign-in or clock change, distinct replacement PID and actual authenticated account; independent server availability is offline. No proxy token-family attribution is claimed. |
| Passenger history/support | [Qualified continuation](../redesign/board-alpha-evidence/v20-native-passenger-existing-history-review-r2.json) passes for existing completed fixture `8145b32e`, its paid receipt, public support acknowledgement and disabled empty Send; business state unchanged. A launcher-created activity initially opens the map; reopening Account reveals the selected detail without choosing a history row again. The initial visibility failure is preserved, not seamless pane-restoration acceptance. |
| Post-expiry entry / account styles | Repeated driver activity entry after controlled expiry passes. [Eight role/style checks](../redesign/board-alpha-evidence/v20-native-account-style-verification-20261022.json), both Notepad process restores and selected 1.3× text pass. Scope is selected account/financial views; no all-page acceptance. |
| Replacement core | First native run stops at the quoted-form recovery defect, before availability/booking commands. Its timed identity beat and earlier no-input foreground-preflight failure remain preserved. No complete v20 trip or board repetition is claimed; fix and freeze a replacement first. |

[22 October endpoint observations](../redesign/board-alpha-evidence/railway-runtime-20261022-auth-required.json)
show API health/readiness and canonical web entries responding, with the shorthand
redirect still wrong. The Railway connector still returns reauthentication after
the owner's reconnection; no fresh five-service topology is claimed. Railway's
[09:28 UTC incident update](https://status.railway.com/) still excludes Trial,
Free and Hobby builds. Keep the exact proxy packet prepared, use `/apply/`, retain
both volumes and remain within the trial. Hosted web v8/API v6 are independent of
the new native build.

**Provider access subsequently restored:** after the owner's normal CLI sign-in,
[fresh explicit staging metadata](../redesign/board-alpha-evidence/railway-runtime-20261022-cli-restored.json)
shows five successful deployments with running instances. The preserved old
volume remains unattached; the active 500 MB trial volume uses about 240 MB.
[The cold-expiry refresh window](../redesign/board-alpha-evidence/v20-driver-cold-expiry-http-20261022.json)
contains one successful refresh and no refresh rejection. Exact family attribution
is not available from proxy fields. [Read-only variable-name inventory](../redesign/board-alpha-evidence/railway-staging-variable-name-inventory-20261022.json)
covers all five services without saving/printing values. No deployment or secret,
billing, volume or staff-access change was made; Trial builds remain provider-paused.

Railway's [21 October security disclosure](https://blog.railway.com/p/security-disclosure-wednesday-october-21st)
recommends rotating stored environment secrets and reviewing service logs. Once
authenticated provider access and Trial rollout are available, inventory the
existing staging secret bindings without exposing values, coordinate database
credential/signing-key rotation with dependent services, and inspect scoped logs.
Do not change a live database credential while its consumers cannot be updated.
Record the resulting deployment identities and invalidate/re-establish synthetic
sessions before the final hosted rehearsal. This is a staging recovery packet;
no specific TaxiMobile secret exposure or completed rotation is established here.

## Retained v19 checkpoint — 21 October 2026

**Current next packet: native session recovery.** V19's later driver presentation
review reaches an actual expired-session sign-in state after background/foreground.
[The preserved rejection](../redesign/board-alpha-evidence/native-v19-session-recovery-rejection-20261021.json)
correlates one successful refresh followed by two rejections. Three driver activity
instances are observed, while each currently constructs a separate credential
coordinator; refresh-to-protected-save is also cancellable. These are hypotheses
being reproduced, not a proven attribution of every request to one token family.
V19's core passes below remain valid within their exact scope, but **full candidate
presentation acceptance is withheld**. Do not bypass the failure with a fresh
sign-in or weaken server refresh-family revocation. Current style review passes
only the passenger cases before the driver failure; replacement work is required.

**Current candidate: native v19 / hosted web v8 / API v6.** The exact shared
sheet correction is frozen and its essential replacement runtime passes. The
visible grabber now expands/collapses through Peek/Half/Expanded while body
scrolling preserves size. Localized accessible snap actions obey text-scale limits.

| Current v19 requirement | Evidence | Scope |
| --- | --- | --- |
| Exact source/build | [Frozen manifest](../redesign/board-alpha-evidence/candidate-native-v19.json): 412 inputs, exactly five native deltas, 377 fresh JVM / 305 Android-host checks, zero failures/errors/skips. | Shared sheet, existing UI regressions and EN/FR/AR action labels; no API/schema/dependency/authority change. |
| Real gesture correction | [Seven native observations](../redesign/board-alpha-evidence/v19-native-sheet-verification-20261021.json), following [actual v18 defect](../redesign/board-alpha-evidence/v18-native-sheet-handle-diagnostic-20261021.json), [source red](../redesign/board-alpha-evidence/sheet-handle-red-20261021.json) and [12 focused green checks](../redesign/board-alpha-evidence/sheet-handle-green-20261021.json). | API31 passenger header up/down and body scroll; JVM child taps/custom actions/font/insets. Full TalkBack remains open. |
| Four-style fare review | [Current native fare/style](../redesign/board-alpha-evidence/v19-native-quote-style-review-20261021.json): all four options retain selected labels, backend fare and enabled Request; same process and unchanged ride list. | Actual English passenger UI; no booking sent in this advisory review. |
| Complete board path | [Fresh integrated verification](../redesign/board-alpha-evidence/v19-native-integrated-verification.json): rides `8145b32e` / `46f115c7`, cash completed, driver offline, pending cash zero; timed seven-beat repetitions **8:17 / 8:22**. | English native / Arabic hosted; synthetic only, same passenger process. Normal browser logout/readback/preparation gap disclosed. No continuous-recording or seven-minute guarantee. |
| Command/recovery authority | [First HTTP trace](../redesign/board-alpha-evidence/v19-native-first-http.json), [second](../redesign/board-alpha-evidence/v19-native-second-http.json), [quote resume](../redesign/board-alpha-evidence/v19-native-quote-foreground-refresh.json), [same process](../redesign/board-alpha-evidence/v19-same-instance-rebooking.json), [14-second reconnect](../redesign/board-alpha-evidence/v19-native-controlled-reconnect.json). | Eight successful business POSTs each once per trip; second actual passenger arrival/in-progress captured. Advisory/auth requests are separate; no business input while offline or command replay. |
| History/support | [Current role review](../redesign/board-alpha-evidence/v19-native-history-support-verification.json). | Both selected details survive foreground/live wait; passenger paid receipt/public acknowledgement and empty Send disabled. First driver search budget expired before history; preserved failure and viewport continuation pass. |
| Staging | [Five healthy services / no pending work](../redesign/board-alpha-evidence/railway-runtime-20261021-v19.json). | Provider still pauses builds/deployments at 17:45 UTC; exact proxy repair remains prepared, undeployed. |

Current role/style restart, enlarged-text and language presentation observations
are being completed on v19. Earlier v18 presentation and bounded OS-motion records
below retain their exact candidate identity; they do not imply all v19 views passed.

The previous tested core is **native v18 / hosted web v8 / API v6**, using only
synthetic Casablanca accounts, GPS and cash. The selected options are
**Folded Streets, Street Press, Glazed Machine and Notepad**. There is no separate
palette menu or main city/taxi illustration.

V18 passes two complete Arabic native lifecycle/cash journeys, quote preservation
through foreground catch-up, same-process rebooking, current history/support and
bounded network recovery. Two actual seven-beat board repetitions pass at **6:54**
and **9:37**, with the read-only QA/reset gap between them explicitly recorded.
They are not an uninterrupted recording; the second includes controlled recovery.

The final bounded display packet replaces technical history UUIDs with short
references and rounds coordinate fallbacks for display only. Both strengthened UI
cases fail before the correction and pass afterward. [The exact v18 freeze](../redesign/board-alpha-evidence/candidate-native-v18.json)
contains 412 inputs, only three native deltas from v17, and passes 372 fresh JVM /
305 Android-host tests. Full API identifiers and original routing points remain.
Current eight-style, qualified restart and 1.3× text checks pass; actual French and
English core views pass alongside the Arabic journeys. [Eight actual welcome
renders and four raw clips](redesign/board-alpha-evidence/v18-native-presentation-review.json)
are recorded and both existing accounts restored. V17 remains the preceding fallback.

## Retained v18 evidence and its scope

| Requirement | Authoritative evidence | Boundary |
| --- | --- | --- |
| Native build and configuration | [V18 manifest](../redesign/board-alpha-evidence/candidate-native-v18.json): 412 frozen inputs, 372 fresh JVM / 305 Android-host tests, exact staging/map-only APK hashes. | Debug Android candidate; no iOS or store-release acceptance. |
| Quote/history ownership | [74 focused checks](../redesign/board-alpha-evidence/navigation-owner-token-green-20261020.json), following [quote failures](../redesign/board-alpha-evidence/quote-refresh-red-20261020.json) and [rotation failures](../redesign/board-alpha-evidence/navigation-owner-token-red-20261020.json). | Fresh server projections, stable login/logout owner, token-specific socket generations retained; no ride-command replay. |
| Passenger/driver/cash | [Integrated verification](../redesign/board-alpha-evidence/v18-native-integrated-verification.json): rides `57bb0f9a` and `93df2c70`, both completed, cash completed, driver offline and no pending cash. | Native Arabic runs on the frozen APKs; fresh owner-scoped readback on 21 October. Synthetic GPS/data/money only. |
| Command authority | [Exact native records/readback](../redesign/board-alpha-evidence/v18-native-integrated-verification.json) and [supplemental HTTP traces](../redesign/board-alpha-evidence/v18-native-http-verification-20261021.json) confirm eight availability/lifecycle/cash commands once per run. | Earlier log retrieval failed; both windows are successfully read after API restoration. Quotes/routes/location/auth are separate from the eight-command count. |
| Retry and reconnect | [Same-process reset](../redesign/board-alpha-evidence/v18-same-instance-rebooking.json), [quoted-form resume](../redesign/board-alpha-evidence/v18-native-quote-foreground-refresh.json), [controlled reconnect](../redesign/board-alpha-evidence/v18-native-controlled-reconnect.json), [actual passenger phase](../redesign/board-alpha-evidence/v18-native-passenger-live-phase.json). | Fourteen-second requested radio interruption, no business input while offline, server remains in progress, then normal completion. Not unknown-command-outcome or field continuity acceptance. |
| History and support | [Current role review](../redesign/board-alpha-evidence/v18-native-history-support-verification.json): short selected references survive foreground/wait; paid receipt, public support acknowledgement, empty Send disabled, business state unchanged. | Original simultaneous ADB observation timeouts are retained; unique r2 attempts pass. No populated driver feedback claim when the API response is empty. |
| Presentation | [Current presentation](../redesign/board-alpha-evidence/v18-native-presentation-review.json): eight welcome renders, eight role/style account/financial checks, Notepad persistence, 1.3× text, selected EN/FR/AR and four raw clips. | Driver normal restore exceeded the original 55-second wait, then continued successfully without retry/sign-in; no fast-start, all-page, full TalkBack, frame-cost or physical claim. |
| Native motion | [Seven actual conditions / 49 original native screenshots](../redesign/board-alpha-evidence/v18-native-motion-verification-20261021.json): expressive motion changes then settles, OS scale zero and Notepad stay static, settled pose retained and text/actions unchanged. | Exact v18 API31 passenger English welcome only; original settings/account restored. Not frame-rate/CPU, all-view/lifecycle, iOS or physical acceptance. |
| Timed board path | [First](../redesign/board-alpha-evidence/v18-board-first.json) and [second](../redesign/board-alpha-evidence/v18-board-second.json): identity, native request/assignment/trip/cash, normal staff MFA/Casablanca review, matching applicant status. | Actual durations 414.416 / 577.304 seconds; intervening read-only QA/reset gap disclosed. No application or review mutation in the browser beats. |
| Representative organization | [Matched applicant/reviewer loop](../redesign/board-alpha-evidence/v8-matched-review-correction-20261019.json), [normal staff/applicant readback](../redesign/board-alpha-evidence/v8-final-board-readback-20261020.json), [support privacy](../redesign/board-alpha-evidence/v8-support-participant-privacy-20261019.json). | Web v8; submitted synthetic application revision 7. No inference of every operations control or populated financial reconciliation. |
| Hosted assets | [102 exact-asset/proxy checks](../redesign/board-alpha-evidence/hosted-web-v8-20261018-oct20-final-current.json), healthy services at [21 October check](../redesign/board-alpha-evidence/railway-runtime-20261021-final.json). | Recheck current availability; the added non-canonical applicant redirect remains red and undeployed. |

## Next executable packets

1. Verify frozen v22 expanded/large-text Inbox access on both owned emulators,
   then complete two exact native/board repetitions with fresh server readbacks
   and one-time command traces. V20 credential recovery and v21 quote recovery
   retain their passed scope; do not reopen them as speculative redesign work.
   Preserve all failed attempts and keep final acceptance tied to exact artifacts.
2. When Railway resumes builds, deploy the exact [proxy-only packet](../redesign/board-alpha-evidence/candidate-web-v8-proxy-r1.json)
   to the existing web service. Require 103 hosted checks and normal `/apply`
   HTTPS entry/state, then update [the handoff](../board-alpha-handoff.md). Stay on
   the trial; no native rebuild is needed for nginx.

## Staging and access constraints

Use the working canonical [applicant URL](https://alpha-web-staging.up.railway.app/apply/).
The shorthand `/apply` currently redirects to internal HTTP port 8080; its nginx
correction is prepared but not deployed. Railway's [22 October status](https://status.railway.com/)
still excludes Trial builds at its 13:16 UTC update. CLI access is restored through
the approved normal sign-in. Direct application `/health`
and `/ready` and the web/applicant canonical entry points respond successfully
at this session's check. Keep those observations distinct from deployment acceptance.

Stay within the trial. Preserve the old full volume unattached; do not purchase
an upgrade or delete a volume. The intentionally persistent five-service alpha
and safe shutdown are documented in [deployment.md](../deployment.md). Extra
Casablanca staff roles expired on 20 October at about 11:27 UTC under the approved
24-hour setup; do not auto-renew. Baseline recruitment scope remains, and the
synthetic bootstrap quorum grants are non-expiring. Credentials stay only in the
ignored protected local setup; never copy them into documentation or demo URLs.

Physical Android is deferred by the owner. iOS is unverified on Windows. Place
search remains disabled under the approved map-selection alpha. EN/FR/AR app UI
and RTL are distinct from Valhalla narration, which currently falls back to
English for Arabic guidance. Real transport, real money, legal/operational
acceptance and public release remain [Milestones B/C](../roadmap.md).

The [ten-gate index](../board-alpha-handoff.md#current-ten-gate-acceptance-index)
keeps wider acceptance requirements visible without turning source checks into
release approval. The 213-view ledger is inventory, not runtime acceptance.

## Historical evidence

The [dated checkpoint archive](../history/board-alpha-checkpoints-20261021.md)
preserves the former 750-line chronology, candidate transitions, failures and
qualifications. It is evidence, not a second active roadmap. Domain contracts
remain in their owning documents; [roadmap.md](../roadmap.md) owns task order.
