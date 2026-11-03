# TaxiMobile — Union Demonstration Readiness

## Active rehearsal checkpoint — 15 October 2026

The owner approved the four selected styles, actual application implementation
and Railway staging deployment, then selected continued emulator work. This
supersedes the historical stop below. See [board-alpha.md](board-alpha.md) for
fresh evidence: twelve actual Android style/language welcome renders, two hosted
REST cash lifecycles and one native two-emulator trip through confirmed cash.
Final polish is rebuilding; the twice-run final candidate, protected web FR/AR
rollout, owner visual review and physical evidence remain open. No UD row or AG
gate is accepted solely by this checkpoint.

## Historical rehearsal halt — 12 October 2026

The owner stopped rehearsal and rejected the current UI/UX. Earlier approval to
keep/refine the current direction is superseded by unrestricted visual
exploration and explicit confirmation before executing the
[complete redesign plan](redesign/README.md). Do not resume native testing,
application redesign or deployment from the older checkpoints below. Preserve
the source, cloud services and synthetic evidence. The planning board is not a
working app or accepted demonstration; UX-0/UX-1 follow owner confirmation.

## Active alpha scope and rehearsal — 12 October 2026

[roadmap.md](roadmap.md) is the single task/status authority; its ten AG gates
define Milestone A. The 20-row board below is retained as the wider demonstration
coverage register with its original denominator and historical evidence. Advanced
manual transfers, fixed routes, scheduling, second-city activation and national
analytics are optional additions to A; they are not deleted requirements or
accepted by omission. Keep their UD rows open and disclose them as not demonstrated
unless their real journey is evidenced. A readiness and wider UD coverage must be
reported separately. Every function actually shown needs full scenario evidence.

### Latest local rehearsal — 12 October 2026

**Subsequent correction and staging check:** the HTTP 400 discrepancy described
below was traced to `TrustedHostMiddleware`: `10.0.2.2` was missing from the local
launcher's exact allowlist. The launcher remains bound to `127.0.0.1`, now accepts
the emulator alias, and still rejects `invalid.example` with 400. Seven launcher
tests passed. After restarting only the owned API, the existing passenger app
restored its actual session and map. Before/after native screenshots are
`.tools/alpha-delivery/passenger-before-host-fix.png` and
`.tools/alpha-delivery/passenger-after-host-fix.png`.

Both Android role APKs then assembled for
`https://alpha-api-staging.up.railway.app`. Passenger SHA-256:
`1ab12c66e0992b940e3875de76595539e7177f5d260d2dc7bca872f2c1ebfc43`;
driver SHA-256:
`ec31613ac5c51c110472832b29697573b926e8c7f9d0da487e639d7f38cdacb3`.
The passenger APK installed with preserved app data on the API-35 emulator;
staging rejects the unrelated old local session and the app correctly shows its
welcome screen after hosted compatibility verification. Actual native screenshot:
`.tools/alpha-delivery/passenger-railway-startup.png`. This is Android-to-hosted
startup/session-boundary evidence only. Hosted registration/onboarding, driver
GPS, actual ride/receipt/payment and physical phone journeys are not accepted.
Screenshots are available for owner review; no visual approval is inferred.

The API-35 passenger emulator is running the freshly assembled passenger debug
APK with `API_BASE_URL=http://10.0.2.2:8000`; the previous APK had been built for
a physical device using `127.0.0.1` and was not suitable for this emulator. The
corrected app launches without crashing and reaches the backend host bridge, but
currently displays “The app version could not be verified.” A direct host request
with the same documented passenger build identity returns `SUPPORTED`; a
status-only local debug diagnostic captured HTTP 400 from the emulator app, after
which the diagnostic was removed. The app response does not yet expose why its
identity is rejected, so the request-level discrepancy remains open. Treat the
passenger UI/UX and account journeys as **not accepted**. The
driver AVD was shut down after two simultaneous emulators caused Android System
UI memory pressure; its user data was preserved. No driver journey was accepted.
The API health check returned 200 locally, which is not hosted-service evidence.

Both launch observations, including the initially wrong debug endpoint and the
remaining compatibility gate, are retained under the ignored local path
`.tools/union-demo/1c91d885932249beb9c5163063306e29/`. Do not publish this private
local evidence directory or interpret it as a release artifact. Overall full
journey acceptance remains **0/20**.

The required presentation beats are: passenger requests → synthetic driver receives
private offer → driver accepts → both apps reflect assignment/status → arrival,
start and completion → truthful pending/confirmed synthetic cash and receipt →
authorized operations inspect trip/driver/payment/case records. Run twice on one
candidate through actual APIs. Check app/service restart, network loss and a
verified reset that cannot modify unrelated data. Credentials/device setup belong
in protected storage; publish retrieval/setup instructions, never passwords.
Provide a labeled recording or verified local fallback when presentation network
fails, plus an implemented/planned/provider disclosure sheet. Never present the
fallback as current hosted success. Railway procedure and cost approvals are in
[deployment.md](deployment.md); this documentation task purchased no service.

## Objective and boundaries

Prepare a repeatable, working presentation of the passenger app, driver app and
management web platform, with every function actually shown exercised beforehand
and every required alpha gate accepted.
This is the current delivery priority, not approval to operate a public service.
Preserve the visual identity in [ui.md](ui.md) and the authority rules in
[design.md](design.md). Do not replace unfinished journeys with successful-looking
screens, injected offers, forced ride transitions or pretend payment approval.

The first presentation uses Android passenger and driver applications and the
existing browser operations/applicant surfaces. Two Android devices are preferred;
one physical device plus an explicitly identified emulator can support rehearsal.
The platform shown must be identified: Android evidence does not certify iOS.
The existing iOS and public-release obligations remain in [gaps.md](gaps.md).

Use synthetic people, applications, documents, trips and payment references.
No real passenger transport, recruitment, identity documents or money are allowed
in this internal demonstration. A published demo fare is not a legally approved
taxi tariff. Show zero operator service fee for the cooperative's free-service
example; demonstrate configurable fees separately as synthetic policy, not an
adopted business charge. Paid hosting or third-party provisioning needs explicit approval; follow the
Railway cost preflight in [deployment.md](deployment.md).

Production release work and its T0–T10 gates remain authoritative in
[testing_execution_map.md](testing_execution_map.md). They must not be relabeled
as complete because the union demonstration succeeds.

## Core-function acceptance board

Every row needs an actual recorded mobile/browser journey and its backend result
on the same candidate. API tests support these rows but cannot accept them alone.
`OPEN` means not yet fully evidenced, not that the implementation is absent.

| ID | Core function | Minimum demonstrable result | Full journey status |
| --- | --- | --- | --- |
| UD-01 | Accounts and sessions | Register, sign in, invalid credentials, sign out, restart and revoked-session handling on both roles; no sign-in crash. | OPEN — six emulator checks per role passed; external revocation and phone evidence pending |
| UD-02 | Driver recruitment | Applicant creates/submits a synthetic city application; authorized web reviewer examines it; pending/rejected driver cannot dispatch. | OPEN — web submission/review/rejection evidenced; Android pending |
| UD-03 | Driver and vehicle eligibility | Show reviewed vehicle/credential/city authorization and explicit reasons for ineligibility; approval in one city does not authorize another. | OPEN |
| UD-04 | Availability and location | Driver records fresh GPS and goes online/offline; stale/denied GPS prevents availability; demonstrate foreground-only dispatch and explain its current limitation. | OPEN — exact API-35 driver APK submitted a native emulator fix with preserved acquisition time and 5.0 m accuracy; backend recorded it 2.466 s later and UI showed `Location submitted`. Permission denial, online/offline and stale refusal have prior emulator evidence; background, lock/navigation-switch and physical-device checks remain. |
| UD-05 | Maps and places | Generic muted map renders; pickup/destination search/selection, wrong-city refusal and map/provider/asset failures are usable; no browseable online taxis. | OPEN |
| UD-06 | Quote and new booking | Passenger sees server fare/payment methods, submits one request; repeated taps/retry create no duplicates; idle/unmatched state is explicit. | OPEN — actual quote and one new booking/unmatched outcome evidenced; refresh timing and duplicate-retry journey pending |
| UD-07 | Driver choice and assignment | Eligible driver receives a new private offer, declines one and accepts another; passenger sees only the assigned driver; unavailable/ineligible driver cannot accept. | OPEN — actual emulator decline and acceptance evidenced; acceptance-time GPS guard and negative journeys pending |
| UD-08 | Assigned ride and coordination | En-route, arrival, start and completion appear on both devices; fresh assigned-driver tracking and closed-code messages work; unrelated passengers cannot track/message. | OPEN — en-route/start, native driver completion and passenger completed receipt evidenced; arrival REST recovery and coordination still need full acceptance |
| UD-09 | Navigation | Pickup/destination route and instructions load through configured routing; loss of routing is explicit, not a fabricated route; actual device map/navigation tested. | OPEN — real provider and authenticated backend routes evidenced; device journey pending |
| UD-10 | Cancellation and recovery | Passenger/driver cancel allowed states; explain reason/status; no stranded offers, duplicate assignment or invalid post-completion cancellation. | OPEN |
| UD-11 | Cash, receipt and earnings | Completion creates pending payment; driver confirms synthetic cash; passenger cannot settle; receipt, immutable economics and earnings agree; replay does not double count. | OPEN — retained cash settled through current driver UI and earnings recovered after restart; same-candidate end-to-end/replay/physical journey remains pending |
| UD-12 | Manual transfer | Enable only a synthetic verified recipient; show instructions/reference, submission still pending/processing, scoped reconciliation/rejection/retry and receipt. No card/CMI promise or real transfer. | OPEN |
| UD-13 | Fixed routes | Passenger sees published endpoints, direction, stops, fare and map even with all drivers offline; request follows route authorization and the backend fare. | OPEN |
| UD-14 | Scheduling | Review total/surcharge/cancellation terms, create/cancel booking, driver opt-in/offer/commitment and conflict refusal; rehearse due handoff with a controlled clock in automated tests and a real-time device case. | OPEN |
| UD-15 | City rollout and tariffs | Web administrator prepares a second synthetic city/configuration, service boundaries, tariffs and flat/percentage fee examples; independent authorized review/activation enforced; passenger catalog respects rollout status. | OPEN |
| UD-16 | Operator control and analytics | City-scoped reviewer cannot control unrelated cities; maker cannot approve own high-impact change; aggregate metrics retain privacy suppression; show config/version/audit history. | OPEN |
| UD-17 | History, feedback and support | Passenger/driver history and receipt reopen after restart; rating and scoped driver feedback work; synthetic support/safety cases reach authorized operations. Do not represent emergency reporting as staffed emergency response. | OPEN |
| UD-18 | Inbox and live delivery | New addressed events refresh the right client/inbox; disconnect/reconnect catches up via REST; test foreground and background delivery separately. No FCM/APNs success claim without OS-level delivery evidence. | OPEN |
| UD-19 | Language and usability | Repeat essential booking/driver flows in French and Arabic/RTL; check English, keyboard, readable errors, permission refusal, small screens, missing assets and basic assistive navigation. | OPEN |
| UD-20 | Repeatable presentation | Start from documented synthetic state, run the whole script twice, restart services/apps once, test Wi-Fi loss and retain a clearly labeled recording fallback. | OPEN |

Wider demo coverage is `fully evidenced UD rows / 20`; alpha readiness uses
the separate ten-gate checklist in [roadmap.md](roadmap.md). Never derive it from the
approximately 84% weighted engineering estimate in [readiness.md](readiness.md).
The current board has **0/20 full journeys accepted (0%)**; substantial source and
backend evidence already exists, but it is not a physical presentation rehearsal.
Do not reduce the denominator to exclude a failing core function.

## Preparation phases

### D1 — Coherent synthetic environment

1. Create a dedicated loopback development database, apply migration
   `20260908_0052`, and keep it separate from user development and CI databases.
2. Use the `union_live` seed profile, not the preassigned `ux_review` scene.
   The approved driver starts offline with **no seeded live location or active
   immediate ride**. The mobile client must capture GPS before going online.
3. Keep fixture login material only in a private ignored local file or in memory.
   Never copy it into docs, screenshots, evidence, Git, Engram or presentation slides.
4. Disable real push/pager/transfer credentials in the demonstration environment.
   Provider simulation is allowed only in explicitly labeled automated tests;
   the presentation must not describe simulation as actual delivery/navigation.
5. Verify seed safety, quote/configuration coherence, public catalog, matching,
   ride lifecycle, cash settlement authority, receipt and replay on real PostGIS.

The existing seeder is **not a reset tool**. It creates unique accounts, preserves
existing configured routes and replaces Casablanca's active synthetic bundle and
on-demand immediate/scheduled tariffs and scheduling policies. Re-running adds
another cohort and future bookings. Do not seed
a user database casually, or discard its data to get a clean presentation.

Seeded schedules are relative to seeding time: a committed fixed route at +4 hours
and an offering on-demand booking at +8 hours. Their policy windows continue to
advance in real time. Do not assume yesterday's fixtures remain a fresh demo.

For an already isolated, migrated development environment, the backend command is:

```powershell
python -m taximobile_api.operations.ux_demo_seed --confirm CONFIRM_LOCAL_UX_DEMO_DATA --profile union_live --output <new-file-in-private-ignored-directory>
```

The legacy PowerShell wrapper accepts `-Profile union_live`, but uses the database
named in `infra/.env`; it does **not** create an isolated demo database. The
`union_live` profile also requires `-OutputPath`: a new credentials file inside an
existing private ignored directory. CLI reservation refuses an existing file or
missing parent before seeding. Credentials are not printed with `--output`;
legacy `ux_review` without an output path still prints them. On Windows, protect
the output directory ACL; POSIX files are created owner-only. Prefer the dedicated
launcher below instead of manually selecting a database for a union rehearsal.

### Local launch, resume and stop

From the repository root in Windows PowerShell 7:

```powershell
.\infra\scripts\start-union-demo.ps1 -ConfirmSyntheticDemo
```

Prerequisites are the existing portable PostGIS cluster, `infra/.env` local
database credentials and the installed backend virtual environment. The launcher
does not install dependencies or alter the database named by `POSTGRES_DB`.
It creates a uniquely named `taximobile_union_demo_<id>` database, verifies that
the loopback database port belongs to this workspace's portable cluster, applies
migrations and seeds once. No database is dropped or reset. The default API port
is 8000, matching the current web client's local endpoint; an occupied unrelated
port is refused, not taken over.

The printed demo ID identifies `.tools/union-demo/<id>/`. `accounts.json` holds
the generated synthetic login details. `state.json` also contains the private
demo JWT signing secret and process identity; **do not share either file**. The
directory has a current-account-only Windows discretionary ACL, inherited by
child files, and is ignored by Git. This does not protect against a privileged
local administrator or replace production secret management.

Resume and stop use that exact ID:

```powershell
.\infra\scripts\start-union-demo.ps1 -ConfirmSyntheticDemo -DemoId <printed-id>
.\infra\scripts\stop-union-demo.ps1 -DemoId <printed-id>
```

Resume reuses the database, account cohort and JWT secret; it does not reseed,
retarget ports or automatically reset failed preparation. Stop verifies executable
and creation-time ownership, including the direct CPython child used by Windows
venv launchers, before stopping only that API. Shared PostgreSQL, all databases,
private logins and logs remain intact. Commands serialize on the demo's lock and
re-read ownership after acquiring it. A readiness observation timeout is not
permission to start another instance: inspect/resume that same recorded ID.

The API runs only on `127.0.0.1`, with development operations-password access and
an exact `http://127.0.0.1:8080` browser origin. Inherited TaxiMobile/provider
configuration is cleared for the child process and restored in the caller;
real Firebase/pager/manual-transfer credentials are not imported. Geocoding is
disabled and routing points at a separate loopback service on port 8002.
Valhalla remains the default; an explicit `-RoutingProvider graphhopper` selects
the already-approved alternative. The selection is recorded with this cohort
and preserved on resume. Legacy records mean Valhalla. To change providers,
stop only this exact demo API and resume its same ID with the explicit selection;
a live API cannot be retargeted, and the database/accounts/JWT are not replaced.
The launcher does **not** provision that service, maps, OS push or real payment
providers. Missing provider behavior must remain explicit during rehearsal.

### Native local routing when Docker is unavailable

`infra/scripts/start-union-routing.ps1` can run the existing pinned GraphHopper
11.0 standalone JAR with an installed Java 17+ runtime. This is an optional
Windows rehearsal tool, not a change to production topology or the default
provider. It uses the reviewed container car/profile configuration, changing
only the HTTP/admin bindings to `127.0.0.1:8002` and `127.0.0.1:8003`. The JVM
has a 3 GiB heap ceiling and two active processors; import/cache disk and total
native process memory still need observation. Pause the owned emulator during
initial country-graph import if this workstation is under memory pressure;
never clear its app data just to free memory.

Download the pinned public inputs into the existing private demo's `routing/`
directory. Verify the JAR against the SHA-256 in the reviewed Dockerfile.
The current example extract is the dated Geofabrik Morocco monthly archive
`morocco-260901.osm.pbf`, 243,256,747 bytes. On 2026-10-04 the complete download
matched its [official MD5 sidecar](https://download.geofabrik.de/africa/morocco-260901.osm.pbf.md5)
(`0372c9ec6dfe895e135f0a2f58ed3e88`); its independently calculated SHA-256 is
`78334b24b7e8913b0153ad866f4806279d41cd11a91f97f17e7102621cc6b1d9`.
MD5 is only a publisher transfer cross-check, not the executable/input security
pin. The expired August daily extract in the previous example returned 404;
never silently substitute mutable `-latest` data or an unverified digest.
Keep the verified owned artifact for repeatability, since even dated remote
archives are not guaranteed permanent. Source data is OpenStreetMap, ODbL 1.0;
see the [official extract page](https://download.geofabrik.de/africa/morocco.html).
This test archive's age is not a claim of current road coverage.

Example (substitute the printed demo ID and actual installed Java/input paths):

```powershell
.\infra\scripts\start-union-routing.ps1 -ConfirmSyntheticDemo -DemoId <printed-id> `
  -JavaPath <installed-java.exe> -JarPath <demo-routing-directory\graphhopper-web-11.0.jar> `
  -OsmPath <demo-routing-directory\morocco-260901.osm.pbf> `
  -OsmSha256 78334b24b7e8913b0153ad866f4806279d41cd11a91f97f17e7102621cc6b1d9
```

The launcher verifies both hashes before executing the JAR/import, refuses
linked/out-of-directory input paths and occupied ports, and records executable,
PID, creation time and command identity. Engine, extract and reviewed config
identity name the graph cache. Re-running observes the same live owned process,
not a second importer. Its private `routing-state.json` and stdout/stderr files
are separate from API ownership; API stop does not stop routing. No automatic
download, cache deletion, provider failover or shared-service termination occurs.
For manual stop, validate the recorded identity with `Get-UnionRoutingProcess`
from `_union-routing-common.ps1` before stopping only that returned process.

Import can take time. Launcher success or `/info` HTTP 200 is **not** route
acceptance. From `backend/`, run the actual provider gate:

```powershell
.\.venv\Scripts\python.exe -m taximobile_api.operations.routing_acceptance `
  --provider graphhopper --base-url http://127.0.0.1:8002
```

This checks nine real normalized routes (Casablanca/Rabat/Marrakech ×
English/French/Arabic), including endpoints, plausible distance/duration,
maneuvers, distinct localized narration and Arabic script. Keep its report and
input/engine/config identities. Only after it passes, explicitly select this
provider for the same stopped API cohort. Authenticated backend routing and
actual mobile quote/navigation, taxi-specific restrictions, accessibility,
wrong-city behavior and physical-device validation remain separate checks.
Geocoding is still disabled; the documented map-tap/manual-coordinate fallback
is not a claim that online place search works.

For the web surfaces, use the existing installed JDK and run from `TaxiMobile/`:

```powershell
.\gradlew.bat :webApp:jsBrowserDevelopmentRun --no-parallel --console=plain
```

Open `http://127.0.0.1:8080/` for operations and `/#/apply` for the applicant
portal. The web dev-server fragment binds loopback, disables automatic browser
window opening and serves generated assets/resources rather than the project
source directory. Production bundling and the visual identity are unchanged.
The current seed's reviewer login supports city-management, recruitment and
aggregate views; broader national/finance/support demonstrations still require
the proper synthetic grants and independent checker described below.

### D2 — Actual Android and browser journeys

Install both role-specific debug applications, verify they reach the same demo
backend and use the expected map/routing configuration. Use the existing Android
device launcher; debug APKs are test installs, not production signed releases.
Recheck backend reachability and ADB reverse after every phone reconnect.
For this loopback cohort, build both Android debug flavors from `TaxiMobile/`
with the explicit `-PtaximobileDebugApiBaseUrl=http://127.0.0.1:8000` property and
reverse the authorized transport's TCP 8000 to host TCP 8000. Do not install a
default `10.0.2.2` emulator-only artifact on a phone or assume that alias is
accepted by this API's exact loopback host policy. Record the installed APK
digest, not just the latest build directory.

Exercise UD-01 through UD-19. For each row retain candidate identity, exact setup,
device/browser version, actions, expected/observed states, sanitized screenshots
or recording and relevant authoritative API/database result. Record failures
explicitly. Browser boot/component tests are not complete reviewer journeys.

For the signed-out registration/session slice, the direct Android harness can
exercise each role without clearing application data:

```powershell
python TaxiMobile/scripts/android_registration_smoke.py --adb <adb-executable> --serial <authorized-transport> --role passenger --session-checks --output <new-private-report-path>
```

Repeat with `--role driver`. Use `--allow-emulator` only for explicitly labeled
simulation. Start from the known signed-out synthetic test state; do not silently
log out an owner's real account or clear device data. The opt-in session checks
exercise wrong-password rejection, successful authentication, force-stop/restart,
UI sign-out and signed-out restart. Signed-out UI proves local session clearing,
not successful server revocation during a transport failure. External revocation,
background behavior, degraded networking and physical-device acceptance remain
separate checks. The driver success screen is the current city-based recruiting
workflow, not the legacy single-application gate or dispatch approval. The harness
searches within observed scroll containers in both directions; it must not swipe
the map to find a sheet control, print field values or reset existing data.
For existing seeded email accounts, the harness's
`submit_existing_email_login` follows the actual Phone/Email segmented selector
and the `email` field. Recovery's `account_identifier` is not the login field.
It refuses an unknown/already-authenticated screen instead of automatically
logging out someone else. Input allows the cohort password's `!` only within
the bounded whitelist and single-quotes that token for Android's shell;
shell substitutions, separators, quotes and spaces are still refused. Do not
weaken/reset the generated cohort password just to automate login. Submission
alone is not success: verify the corresponding backend-driven role screen.

Recruitment, finance and national city governance require the correct synthetic
staff grants. The current UX seed includes one city manager/reviewer/analyst, not
a national administrator, finance team or independent checker. Extend fixtures
through the existing staff/bootstrap authority; do not bypass maker-checker rules
or make the sole reviewer approve their own changes to make the demo easier.

#### Recruitment rehearsal (UD-02, with UD-03 eligibility checks)

1. Open `http://127.0.0.1:8080/#/apply` in an applicant browser session and the
   operations root in a separate reviewer session. Read logins only from the
   private account file. Use `passenger_empty` to start a synthetic application;
   use `operations_recruitment` only in the protected console.
2. Start a Casablanca application. Confirm the active requirement version and
   applicant-owned profile reference. The compatibility requirement is not a
   real licensing checklist; do not describe its completion as legal eligibility.
3. Submit for city review. Confirm `SUBMITTED`, a single submission revision,
   no city authorization and no usable online availability. Repeated submission
   must not create another application or revision.
4. In the console, explicitly select Casablanca, open Driver recruitment, then
   review the same applicant in the scoped queue. Start review with an allowed
   reason, a synthetic applicant-safe message and the review confirmation.
5. Refresh the applicant portal while its detail panel remains open. Both the
   summary card and detail/timeline must show `UNDER_REVIEW`, the current record
   version and the safe message. Refresh must fetch detail, not retain old status.
6. Rehearse rejection with a documented reason and a clearly synthetic message.
   Refresh the applicant again: card, detail and latest decision must agree on
   `REJECTED`; the account must still lack dispatch authority. A rejected record
   cannot be resubmitted. A new application, where allowed, is a new retained
   record, not a reset of the rejected one.
7. Retain private screenshots and check the API facts, ownership refusal and
   online refusal. Separately test the approved-driver/vehicle path and Android
   client. No missing scanner/storage may be bypassed to present upload success.

These actions change only the isolated synthetic cohort. For a clean rehearsal,
launch a new demo ID; do not wipe or silently rewrite this cohort's history.

### D3 — Failure rehearsal and presentation

Run denied/stale location, declined/unmatched offers, repeated command taps,
offline/reconnect, app restart, map/routing outage and expired session cases.
Inspect crashes rather than hiding them with forced success. Then run a concise
20–30 minute presentation twice from known state:

1. Explain taxi ownership, free-service example and city-by-city deployment.
2. Show fixed-route catalog with the driver offline.
3. Go online, request a new ride, demonstrate driver choice and the ride states.
4. Complete, confirm synthetic cash, inspect receipt, history and earnings.
5. Show scheduling and a clearly labeled manual-transfer rehearsal.
6. Walk through application review, city/tariff governance and aggregate analytics.
7. Show languages, one network recovery and limitations honestly.

A fallback recording must identify its candidate and be described as recorded,
not live. A recording is contingency for the meeting, not a replacement for
verified live journeys. Keep public deployment blockers visibly separate.

## Current implementation evidence

The seed has two explicit profiles and guards its callable as well as the CLI.
Both profiles bind the active city service to the new active immediate tariff,
preserve configured payment capability references, and generate synthetic history
through the existing fare/economics/payment helpers. A completed pending-cash
ride is no longer incorrectly advertised as cancelled in the seed inbox.

On 2026-10-02, the guarded local runner passed **19 focused cases: 15 unit/CLI
safety cases and four migrated PostGIS integration cases**, with zero failures,
errors or skips. Its retained JUnit is
`backend/build/union-demo-focused-20261002-v3.xml` (ignored local evidence, not a
clean immutable CI artifact). The source credential gate, 83 HTTP + one WebSocket
mobile contracts, 112 web HTTP contracts, documentation gate, four documentation
validator tests and the PowerShell wrapper syntax check also passed.

The integration cases prove both profiles work with a previously pinned tariff,
historical receipts carry current-format economics, public routes remain visible
offline, notification/ride facts agree, and repeated seeding preserves existing
accounts without overlapping active pricing/policy intervals. The fresh-request
case proves missing location/pending driver refusal, accepted location/online,
actual dispatch, command replay, driver acceptance, every ride transition, pending
then driver-settled cash, passenger settlement refusal, receipt and rating.

This is a **selected seed/HTTP/worker test pack**, not a new full backend regression.
It does not prove rendered maps, physical GPS, OS push, navigation, browser staff
flows, field service or a presentation. All UD rows remain open pending their
full actual-client journey evidence. No source/UI/database schema was replaced
to make a test pass; existing authority and business rules remain in force.

The next local setup slice passed **seven native Windows launcher safety tests
and three actual Node webpack-fragment tests**. A fresh isolated launch and live
stop/resume were exercised: the API listener stopped, the owned API process
changed on restart, database/login files were preserved, the existing passenger
session remained usable and the quote remained 35 MAD with cash only. Shared
portable PostgreSQL remained running. Resume then revalidated the owned cluster
without reseeding. These are local lifecycle facts, not release acceptance.

The browser verification skills required a real rendered/API check after server
startup. Local Chrome through agent-browser loaded the API documentation and
the actual operations sign-in, authenticated the seeded city reviewer, rendered
rollout/recruitment surfaces and selected Casablanca. The constrained rebuilt
web server listened only at `127.0.0.1:8080`; `/build.gradle.kts` returned 404, and
the inspected browser session reported no page errors. Private screenshots are
inside the ignored demo directory. This verifies boot, sign-in, navigation and
scope selection only, not applicant submission, document review, finance,
maker-checker/city activation, the browser matrix or a complete UD row. Source
warnings about npm/configuration performance and macOS-only native tests were
not relabeled as failures or hidden by this patch.

### Recruitment and applicant refresh verification (2026-10-02)

The actual local browser rehearsal advanced a synthetic application through
`NOT_STARTED → SUBMITTED → UNDER_REVIEW → REJECTED` using separate applicant and
authorized city-reviewer sessions. The reviewer inspected the scoped record,
used allowed reasons and applicant-safe messages, and confirmed each decision.
The approved-driver seed and all real-world eligibility requirements were left
unchanged. Protected document storage remained unavailable; no upload or legal
document review was claimed.

The first reviewer decision exposed a real refresh defect: the applicant summary
advanced to version 3, while the open detail remained at version 2 / `SUBMITTED`.
`ApplicantPortalCoordinator` now retains the selected ID but fetches its current
server detail on every owned-data reload, including refresh and vehicle changes.
After rebuilding, a second browser decision and applicant Refresh displayed
`REJECTED` consistently in the summary, open detail, timeline and latest message
at version 4. The live API confirmed no city authorization, a pending driver
account, offline availability and HTTP 409 / `Driver account is not active.`
when that account attempted to go online. Private screenshots remain in the
ignored demo directory; do not publish account material or restricted detail.

The full **61 Kotlin/JS browser tests passed with zero failures/errors/skips**,
including four new real-coordinator regressions for fresh reviewer status,
retained selection, changed vehicle completeness and explicit refresh failure.
The Wasm main source compiled; that is not a Wasm browser acceptance test.
The guarded selected backend pack passed **20 cases: 15 seed unit/CLI and five
migrated PostGIS integration cases**, zero failures/errors/skips, retained at
`backend/build/union-demo-recruitment-20261002-v3.xml`. The added case exercises
the seeded reviewer, applicant ownership, self-approval payload refusal,
duplicate submission/decision replay, rejection, safe decision visibility,
blocked offline GPS, and online refusal before and after rejection. The source
credential and mobile/web contract gates also passed. This remains a selected
backend pack, not a full backend regression or device certification.

Browser automation needed two precautions: this Compose build exposes offscreen
semantic controls with zero bounds, and the inspected CLI wheel command delivered
events at `(0,0)` despite moving the pointer. Content-targeted wheel events plus
screenshots were used to reach the forms. After a scope popup closed, some
semantic snapshots also retained popup content while the visible interface
changed; observed-coordinate interaction was required in that reviewer session.
These limitations must not certify keyboard/screen-reader accessibility, and
must not be mistaken for proof of an application scrolling defect. Actual
browser/device accessibility still belongs to UD-19.

UD-02 has meaningful browser/API evidence, but its Android path and the separate
approved-driver/vehicle journey are not accepted. The full presentation board
therefore remains **0/20 accepted**, with this partial evidence retained rather
than treating the row as absent or silently closing it.

### Android artwork and test-fidelity follow-up (2026-10-02)

A connected, authorized Samsung SM-A065F running Android 16 accepted both updated
debug-role APKs without uninstalling either product or clearing local app data.
The first passenger launch crashed in the welcome illustration because Android's
Compose resource loader rejects SVG. This is an observed physical failure, not
a backend/sign-in rejection. The replacement optional-artwork path uses bounded
PNG exports and keeps the accessible Canvas/text fallbacks during loading or
on decode failure; cancellation/fatal VM errors are not swallowed. The owner
then changed the welcome direction: navy background and outlined taxi/Moroccan
architecture. The code-authored outline was rejected; the owner explicitly asked
for image generation, thin light-navy strokes, then a taller phone composition and
less dense detail. The selected approximately 4:5 PNG and prompt/provenance records
are bundled locally. Earlier unDraw/vector/3D candidates are not runtime sources.
It is decorative only and requires no runtime image-generation/stock service.
Only welcome artwork proportions/fallback changed; brand controls and operational
maps are unchanged. Final owner approval and physical-phone verification remain
open; the portrait has now been inspected in the actual API-35 Android emulator.

The registration harness now binds ADB commands to one authorized transport and
records explicit physical/emulator fidelity in schema 2. Emulator use requires
an explicit opt-in and cannot produce `ANDROID_DEVICE_REPORT` credit. The
single-device metadata flag remains false when an explicit selection is made
from multiple connected transports. Reports must retain the partial T4 and
deployment-not-accepted flags. No existing-data wipe is permitted merely to get
a clean report; use the known signed-out test state or review that choice first.

Post-fix phone results must be recorded here after execution, including failures.
Do not accept UD-01, UD-05 or UD-19 solely from an APK build, asset preview, unit
suite or successful activity-start command.

The post-fix passenger APK installed and its activity started on the phone, but
the registration harness timed out awaiting `message_account_created`. The USB
transport subsequently disconnected before diagnosis. This is **not** a passing
registration/login journey, and its cause is not yet established. A fresh owned
API-35 emulator is available for explicitly labelled simulation; it cannot replace
physical-phone acceptance. No existing phone data was cleared.

### Portrait layout verification (2026-10-03)

The selected 1122x1402 sparse navy/light-navy illustration renders in the driver
app on the owned API-35 Android emulator at 1080x2400. A fresh screenshot was
visually inspected: the whole taxi and minaret remain visible, the header clears
the status bar, and both account actions fit above the system navigation area.
The accessibility hierarchy exposes the artwork description and both account
actions. This confirms this emulator welcome screen, not multilingual, large-font,
screen-reader, registration/login, physical-device or deployment acceptance.
Both updated debug-role APKs installed without clearing existing application data.
The shared JVM suite passed **247 tests**, with zero failures/errors/skips;
the mobile tooling suite passed **89 tests**. Both Android debug builds and
JS/Wasm main-source compilation passed. Graphic, documentation and source
credential validators passed. Portrait sizing and safe-inset offset have focused
Compose regression tests; corrupt/missing decorative assets retain their fallback.

The preview initially encountered Android System UI unresponsiveness under host
memory pressure, then an explicit connection-unavailable screen because the local
API/database were stopped. The native Wait action and build-JVM garbage collection
allowed the emulator to recover. PostgreSQL recovery exceeded the launcher's
30-second startup limit; a bounded 120-second database start completed, and the
same demo resumed with its existing database and accounts, without reseeding.
These interruptions are recorded rather than counted as product acceptance.
No physical Android device was authorized during this verification. The union
presentation board remains **0/20 fully accepted journeys**.

### Account journeys and safe-area repair (2026-10-03)

On the API-35 emulator, the passenger account control's original bounds placed
its centre at y=106 inside the actual status-bar frame y=0..128. Tapping its
visible lower edge opened the account sheet, establishing a safe-area defect,
not a failed account endpoint or proof that MapLibre intercepted all touches.
Both role toolbars now consume top/horizontal safe-drawing insets and use the
documented side/vertical spacing and 48 dp control height. The passenger account
action now occupies y=160..286 and opens the account sheet from its centre.
Its localized account-purpose description supports accessibility and testing
even when the displayed label is a user's name. Driver onboarding also respects
safe insets, and sheet scroll content stays above gesture navigation.

The test harness had separate defects: it expected the superseded driver
`apply_to_drive` gate instead of current city onboarding, swiped outside the
passenger peek sheet, searched only four pages, and appended input to retained
drafts. It now searches observed scroll containers to an edge and back, skips
text-field scrollers, respects disabled ancestor controls, replaces only the
focused bounded synthetic field, and retries only Android's transient null-root
response. It does not relax registration/backend-screen confirmations or reset
device data. Installed base/split APK SHA-256 digests are recorded without their
device paths, so evidence is not identified solely by the reused version label.

The updated working-tree candidate passed **251 shared JVM tests** with zero
failures/errors/skips, **101 mobile tooling tests**, both Android debug builds
and JS/Wasm main-source compilation. Graphics, MapLibre composition, mobile
live-update wiring, documentation and source-credential gates passed. Four new
controlled UI cases cover onboarding, both toolbar actions, and long-sheet action
access above gesture navigation. Initial toolbar-position assertions exposed
40 dp visible TextButton bounds; explicitly enforcing 48 dp fixed the tests and
aligned these controls with the documented touch-target requirement.

Fresh passenger and driver runs each passed six checks through the actual
installed apps and the same local API: account creation, wrong-password refusal,
successful login to the appropriate authenticated product screen, force-stop/
authenticated restart, UI sign-out, and signed-out restart. Both recorded
installed-APK digests match the respective built debug APK. Reports are retained
privately under the current `.tools/union-demo/<id>/` directory as
`passenger-sessions-emulator-20261003-safe-chrome.json` and
`driver-sessions-emulator-20261003-safe-chrome.json`. They explicitly identify
emulator-only execution, debug builds and no phase/deployment acceptance.
Sign-out/restart establishes local token clearing; it does not establish server
revocation under a transport failure. External revocation, broader lifecycle and
weak-network behavior, and physical-device repetition remain open for UD-01.
Android System UI again blocked the initial preview with its own unresponsiveness
dialog; the observed native Wait action restored access before these passing runs.

This does not accept UD-01 or any other full presentation row: the board remains
**0/20 fully accepted (0%)**, with the above twelve bounded emulator checks now
evidenced. Navigation/booking still require a real local routing service on port
8002; Docker CLI is installed but its Linux engine is not currently running.
No provider output, assignment, GPS, payment or approval was fabricated to make
these account checks pass. No phone or emulator application data was cleared.

### Routing rehearsal progress — 2026-10-04

The verified September Morocco archive and pinned GraphHopper 11.0 JAR were
actually imported using the native local launcher. Both observed listeners were
owned by the recorded Java process and bound to `127.0.0.1` only. Re-running
the launcher recognized that same process instead of starting a second import.
The country graph is an actual routing graph, not mocked geometry.

The first real gate exposed a CLI HTTP-client lifecycle defect: two separate
`asyncio.run` calls routed and closed an HTTP transport on different event loops.
The command now constructs, routes and closes on one live loop, including
failure/cancellation cleanup. Four regression cases plus the existing gate and
GraphHopper adapter tests passed (**29 backend unit tests**). Native launcher
and API-cohort confinement/ownership/selection tests passed (**18 tests**).
Local routing/source and documentation validators also passed. These are not
device or public-deployment tests.

`routing/routing-acceptance-20261004.json` under the current private demo records
**9/9 real provider checks passed** (three public city-centre routes × three
languages), with no failure codes. Arabic script and localized narration were
observed through the real provider adapter, not merely a locale parameter.
This validates the bounded gate, not Moroccan road legality or the quality of
every translated instruction. The reviewed baseline car profile does not enable
turn-cost/turn-restriction preprocessing; taxi-specific access and forbidden-turn
coverage still require explicit operational validation before real transport.

Only the owned demo API was stopped and restarted with explicit GraphHopper
selection. The database name, account-file digest and JWT signing identity were
checked unchanged; no seed/reset occurred. The private
`routing/backend-routing-smoke-20261004.json` records **18 authenticated HTTP
routes** (passenger and driver × three cities × three languages), positive
metrics/geometry/maneuvers, localized narration and valid shape indices. Both
short-lived test sessions were logged out through the API; their subsequent
route requests returned 401, as did an anonymous request. This is backend
revocation evidence, not mobile external-revocation handling.

The routing service remains loopback-only and the cohort still has disabled
geocoding. Maps/quote/booking/navigation on Android, provider outage UX, physical
device repetition and every remaining acceptance row are still open. The full
demonstration board remains **0/20 accepted (0%)**. Provider sub-gate progress is
**9/9 (100%)**, not a substitute denominator for the union goal.

### Android quote-form keyboard defect — 2026-10-04

After recovering an observed native System UI Wait dialog, the existing seeded
passenger signed in through the real Android Email control and reached the
backend-driven home sheet. The muted MapLibre street map rendered. This is an
emulator observation, not phone acceptance; no app data was cleared.

Attempting manual quote coordinates exposed a shared sheet defect: opening the
numeric keyboard consumed the entire small peek sheet's scroll viewport. The
focused field disappeared from the Android accessibility tree; the captured
screen showed a blank sheet above the keyboard. This was not a reason to relax
the harness's one-focused-field safety guard or fabricate coordinates.

`TaxiSheet` now reserves/consumes IME bottom space in its outer overlay **before**
computing the requested snap height. The inner scroller consumes remaining safe
insets, not the same keyboard again. Map/background layout, branding and snap
choices are unchanged. An injected-inset regression keeps the input focused and
scrollable when a 300 dp keyboard exceeds a peek sheet, then checks gesture-nav
bounds after hiding it. The full shared suite passed **252 tests**, both debug
APKs built with the explicit localhost API property, and JS/Wasm compilation
passed. All **104 Android/tooling tests** passed, including existing-email
selection, unknown-screen refusal and bounded quoted-password cases.

The same local backend still has no active passenger ride and returns the
synthetic point-to-point quote of **35.00 MAD**, **0.00** operator service fee and
only **CASH**. This is a precondition for the Android journey, not its completion.
The owned emulator was stopped gracefully during compilation to relieve memory
pressure and reopened without wiping data. The first verification attempt then
encountered the session-expired screen; the fresh-login retry is recorded below.

Both rebuilt APKs were installed with `-r`, preserving app data. The first quote
attempt typed all four coordinates successfully, but reached the explicit
session-expired sign-in screen rather than a fare. With a fresh seeded Email
login, the same coordinate/keyboard path completed: the passenger displayed the
backend **35.00 MAD** transport fare, actual **2.8 km / about 3 min** route summary
and turn instructions, a visible muted MapLibre route line, Cash selection and
an enabled Request taxi action. No coordinate, fare, route response or auth state
was injected into the app. Manual coordinate entry is the documented debug/failure
fallback, not evidence for place-search or map-tap selection. No new booking was
submitted by this slice.

Private `passenger-real-quote-20261004.png` was visually inspected;
`passenger-quote-emulator-20261004.json` records seven bounded checks and the
actual installed passenger APK SHA-256
`3d96e7effad112d57b6df1a103a779c658d2f4de1998382dc2d8e3afbd99222d`,
matching the rebuilt artifact. The driver APK was installed, not given a new
driver-journey acceptance claim. Phase/deployment flags remain false, and
**0/20 full journeys** remain accepted. Driver GPS/online/offer decisions,
booking idempotency, real ride transitions, cash settlement, Arabic/French UI
repetition and the remaining rows must still be exercised.

#### Newly exposed authentication inconsistency

[auth.md](auth.md), section 35, requires one bounded refresh attempt after an
expired access-token 401 before retry/final logout. `AuthenticationSessionCoordinator`
already implements serialized refresh during `restore()`, but
`MobileAppCoordinator.estimateRide()` catches `AuthenticationRejectedException`
and returns a signed-out state directly. That ordinary quote failure path does
not call restore/refresh first. Other business-operation rejection paths need
the same audit; the specific observed 401's token timestamp/revocation cause has
not been independently established from retained credentials and must not be
asserted solely from the generic UI message.

This discrepancy is an open UD-01/UD-06 usability/recovery gap, not permission
to extend token lifetimes, bypass revocation or replay irreversible business
commands automatically. Reuse the existing session mutex/generation/cancellation
fences, distinguish read-only retry from explicit non-replaying command recovery,
and test expired access with valid refresh, revoked refresh, network failure,
concurrent rotation and logout races before promoting the change. Until then,
start bounded rehearsals with a fresh synthetic sign-in and keep this limitation
explicit rather than marking refresh continuity accepted.

### Advisory quote recovery and interrupted-service resumption — 2026-10-04

The discrepancy above is now patched for the four advisory quote entry points:
immediate point-to-point, immediate fixed-route, scheduled point-to-point and
scheduled fixed-route. The existing credential mutex owns backend `/me`
validation, at most one refresh attempt total and at most one read-only replay.
The authorized product reload is inside that same boundary. Queued reads capture
ownership before waiting; login/logout fence late projections and cannot allow
old refresh persistence/principal validation to restart live hints. Definitive
revocation stops reads and clears credentials; failed protected-store deletion
is a recovery failure, not successful sign-out. Cancellation is not normalized
as a network error. No business command is in this retry callback.

Fresh final verification passed **284 JVM tests** and **240 Android-host tests**,
including **19** session recovery/ownership/storage tests, **11** actual
coordinator-boundary quote/non-replaying-command tests, and **2** Ktor
cancellation tests on both targets. Both Android role debug APKs assembled with
the explicit `http://127.0.0.1:8000` API property; JS and Wasm shared compilation
also passed. Tooling verification passed **104 mobile-script tests** and
**266 infrastructure-script tests**; live-update and one-shot recovery source
validators passed. These are synthetic/host checks, not a naturally expired
access-token journey on a phone, external-revocation UI acceptance or proof of
every business handler's recovery. Broader command/read rejection handlers still
need the non-replaying audit. Full UD-01/UD-06 acceptance remains open.

Resuming the existing local environment found PostgreSQL performing WAL recovery
after an interrupted host. The old portable launcher's 30-second readiness
timeout terminated startup despite recovery still running. The launcher now
leaves the startup process alive, reports an observation timeout, and directs
the operator to the exact workspace DataRoot's `pg_ctl status`, `pg_isready` and
private logs before resuming. Three native control-flow tests cover slow-live
startup, successful readiness and terminal exit, without touching a database.
Actual recovery then completed (approximately 151 seconds of WAL redo), followed
by `pg_isready` success. No data directory was reset or replaced.

The same demo API resumed and returned ready with GraphHopper selected. The
account-file SHA-256, database name and signing identity were compared before
and after and were unchanged; no cohort reseed occurred. The real routing
service's `/info` returned GraphHopper 11.0 and the car profile. This verifies
local service resumption, not a second full presentation or hosted availability.
The new emulator candidate still needs the remaining full booking/driver/cash
journeys. Installed-artifact identification and the next bounded observations
are recorded below. Full demonstration readiness
remains **0/20 accepted (0%)**; the new targeted recovery checks are **32/32** on
each host target, not a substitute denominator for the union goal.

Both final APKs were installed with `-r`, preserving app data, and their actual
installed hashes were checked against the rebuilt artifacts:

- Passenger: `8d4d1f29c439535e38110fd1b6a4ca7b4dcb3b7d897eec207c3137752dc5ceba`.
- Driver: `5b6359bae40fdc4e59449e0c65964e4abfce16d25b417039bdb67d8b34781904`.

The passenger restored the retained protected session, accepted all four manual
coordinates through the focused-field guard, and displayed the real **35 MAD**
quote, cash choice and **2.8 km** GraphHopper route. The private candidate report
`passenger-recovery-candidate-quote-20261004.json` and visually inspected screenshot
bind this observation to the installed passenger hash. Restoration does not
prove this particular quote exercised natural access expiry or external
revocation; those flags remain unaccepted. The driver candidate was installed,
not given a driver-journey acceptance claim.

The same passenger then submitted one actual Request taxi action. A separately
authenticated, read-only observer verified exactly one new backend ride relative
to the pre-command history. The original harness reached a terminal-state check
but timed out waiting for `where_to`; it is **not** recorded as a passing full
script. Subsequent API observation showed three history records (`UNMATCHED` plus
the two earlier `COMPLETED` fixtures) and no active ride. Android reobservation
showed the booking home and explicit “No available taxis” message, with no fleet
or assigned driver. The visually inspected private screenshot is
`passenger-after-booking-20261004.png`; the corresponding terminal report is
explicitly **PARTIAL**. The initial status was not retained, cancellation was
not accepted, and repeated-tap/network-replay behavior was not exercised. Inspect
the cancellation/state-refresh timing before claiming UD-06/UD-10 completion;
do not force a transition, create another ride blindly or reset this history.

A subsequent **read-only** query confined to this synthetic passenger's latest
ride retained `backend-new-booking-timeline-20261004.json`. Its append-only event
set confirms creation as `REQUESTED`, transition from `REQUESTED` to `MATCHING`
and matching failure from `MATCHING` to `UNMATCHED`, with no cancellation event.
The events share a database timestamp; the UUID tie-break used for retrieval is
not causal ordering or a latency measurement. This supports the terminal result,
not successful cancellation or a measured immediate UI return. The native wait
failure could involve refresh latency, viewport discovery or resource pressure;
its cause is not yet established, so no speculative application fix is claimed.

An additional **70 backend unit tests** passed for authentication security,
matching lifecycle/scoring and cash workload. Those do not replace the remaining
actual assignment, ride, settlement, multilingual and full-repeat rehearsals.

### Two-role native rehearsal and corrective candidate — 2026-10-04

The second owned API-35 Android emulator now runs the same installed passenger
candidate listed above, signed into the existing synthetic passenger. No app
data was cleared, account cohort reseeded, database reset or business state
injected. This is a two-emulator rehearsal, not physical GPS or iOS evidence.

Actual driver permission denial left online entry disabled. Foreground-only
permission and a reviewed OS-simulated Casablanca GNSS fix enabled location
submission and backend `AVAILABLE`; actual Go offline returned `OFFLINE`.
After the server observation aged beyond the configured freshness bound, Go
online was refused. The generic availability error still needs more actionable
guidance. An initially returned unrelated platform coordinate was reviewed and
not submitted; the cause of that platform fallback is not yet established.

One real private offer was declined with the native confirmation and became
`UNMATCHED` with only one eligible driver. Another offer expired rather than
being accepted: the scoped database read proved its approximately 45-second TTL
and expiry, while the driver was still sending foreground observations. Do not
label that failure stale-GPS acceptance. A subsequent actual Accept tap, made
about 16 seconds after request submission, assigned the ride. En-route appeared
on both clients and in the authorized passenger read.

Arrival committed but initially did not refresh the passenger. Inspection found
missing lifecycle outbox producers, not a stopped worker. The correction writes
minimal `ride.updated` hints and generic passenger-owned inbox entries for
en-route/arrival/start/completion/first cash settlement within the business
transaction. The worker reloads current ownership/state; cash replay creates no
duplicate notice. The API was restarted through the exact cohort's guarded
stop/resume path, preserving database, account file and JWT secret. The passenger
recovered arrival through foreground REST catch-up, then a newly committed Start
appeared on both clients. That start hint was delivered once, with an observed
outbox delivery lag of about **1.02 seconds**; this is one local observation, not
a delivery SLO, FCM proof or automatic-arrival proof.

Seventeen focused lifecycle/cash producer-delivery cases and the full **908-test
backend unit run** passed. The earlier targeted push relay run passed on JVM and
Android host. Generic update inbox copy is now present in English/French/Arabic.
The routing regression test now actually mutates both currently pinned extract
URLs, rather than referring to a superseded date. Asset/localization/live-update
source checks remain distinct from device acceptance.

The current ride was started, then moved through ten gradual **OS GNSS inputs**
over about 150 seconds. This is synthetic straight-line movement, not navigation
or physical-location quality proof. Completion coordinates were reviewed in the
native form, but the first control search timed out. Six later UI observations
found Complete ride disabled five times while automatic location work competed
for the single-action gate. A subsequent observed-enabled tap did not yield a
committed completion; the server remained `IN_PROGRESS`. Two natural access-token
expiry boundaries returned the driver to sign-in even though its retained
refresh session remained unrevoked/unexpired. No successful completion, payment,
receipt or earnings acceptance is recorded for this ride.

The corrective mobile source now leaves a state-specific idle interval **after**
the automatic submission/readback/reconciliation releases its gate. Resource
authentication rejection also requests one read-only session restore before
declaring the refresh session lost; the original command is never resent and
never receives a success confirmation from that recovery. Deliberate logout,
revoked refresh and unauthenticated screens remain fail-closed. Four new sampling
policy cases, four native-presentation recovery cases and one coordinator marker
case cover these boundaries. Their fresh full build/test run and rebuilt
candidate-device checks must pass before claiming the correction works on a
device. An intermediate build read inconsistent source snapshots during edits
and failed host compilation; it is not a green candidate. The next build uses
a frozen source snapshot, forced task execution and nonincremental compilation.

Both owned emulators were cleanly stopped to release workstation memory during
that rebuild; their application data was preserved. The demo API and current
in-progress ride were left intact. Resume the same AVDs and install with `-r`,
verify installed hashes, recover the retained ride, then repeat completion,
cash settlement, receipt/earnings and a natural access-expiry journey. Do not
book another ride, force completion or reseed to hide the failure. Immediate
acceptance-time GPS freshness and cached-observation provenance remain open
source gaps in GAP-007. Full readiness is still **0/20 accepted (0%)**.

The frozen, forced/nonincremental run subsequently completed successfully:
**295 JVM tests, 251 Android-host tests**, both role debug APK assemblies,
**108 mobile-tooling tests** and **266 infrastructure tests** passed. Mobile
contracts cover 83 expanded HTTP operations plus one WebSocket; web contracts
cover 112 HTTP operations. Credential hygiene, assets, localization (612 catalog
keys) and live-update wiring passed. No iOS runtime/compiler or release-signing
acceptance is implied. The new emulator-oriented debug artifacts use the existing
`http://10.0.2.2:8000` host alias and muted OpenFreeMap Positron style:

- Passenger built SHA-256: `cfdcfaadfc82606d6ea1044eb14c6b6efc539e6077ee482ad7192b27f54ed812`.
- Driver built SHA-256: `79d6b698ce6699bd4d81be2f9af2321b82cd7fa0f71827fd7f35b12e4b94c8ce`.

These are **built**, not yet installed/rehearsed identities. Both same AVDs were
launched again with their exact preserved workspace data paths; boot observation
is still pending. No physical Android transport was connected at this check.
Phone USB rehearsal requires a separately explicit debug loopback endpoint plus
ADB reverse; these emulator APKs must not be described as phone-verified.

### 2026-10-05 — Artwork refinement and retained-cohort recovery

The owner requested taller phone framing and fewer lines. The selected generated
welcome is now approximately 9:16 (941x1672), with only three pavilion arches,
simplified wheel/headlight contours and no seats or paving grid. It is mirrored
byte-for-byte, fits without cropping at up to 216x384 dp, and retains the existing
accessible Canvas fallback and 2 MiB input limit. The previous 4:5 master is
retained as legacy. Ten graphic-tooling tests, the asset validator and fourteen
targeted JVM layout/decode/fallback tests passed. This is not owner visual
acceptance or a physical-phone check.

The demo API and both emulators were observed stopped before recovery. Resume
preserved the same account cohort, database and in-progress ride; no reseeding,
new booking or forced ride transition occurred. The restarted GraphHopper car
provider passed all nine city/language checks (Casablanca/Rabat/Marrakech,
English/French/Arabic). These are routing-provider checks, not a device-navigation
journey.

Installing the previously built driver APK exposed a configuration mismatch:
its default `10.0.2.2` host header received HTTP 400 from this cohort's deliberately
strict loopback host policy. This is not a sign-in or lifecycle success. The
documented explicit `127.0.0.1` build property plus per-transport ADB reverse is
the corrective path; do not broaden server binding/host policy or use wildcard
hosts. Both role APKs are rebuilding with that endpoint and the new artwork.
Record their actual installed digests and retained-ride recovery before crediting
device behavior. The booting secondary emulator was stopped with its exact
console identity when host free memory fell below 0.5 GiB; its data was retained.
Full demo acceptance remains **0/20 (0%)**.

Both explicit-loopback role APK builds subsequently succeeded and both were
installed with `-r`, their on-device SHA-256 checked, and TCP 8000 reversed on
each exact owned emulator. Passenger digest:
`7ed3524b2a2914cad7ee3554aeae7fa7255ec6605e53c44fda01478d9d1b40e8`;
driver digest:
`bc98ba0b417506d7266d7a0e7c6ba3f29208c3686e40a74997abbd4923846283`.
These supersede the unverified host-alias candidates above. Physical Android,
iOS, production signing and distribution remain unaccepted.

Android System UI and Messages error dialogs obscured the rehearsal; no
TaxiMobile crash was identified in those dialogs. Selecting Wait on the observed
system dialogs allowed the driver to show the retained in-progress ride without
a new login. This is not a proved diagnosis of all emulator performance issues.
Native completion then committed the exact retained ride at 2026-10-05 19:18 UTC:
the backend reported `COMPLETED`, driver `OFFLINE`, fare **35.00 MAD**, operator
fee **0.00**, driver expected net **35.00**, and cash **PENDING**. No direct
business command, new booking or forced transition was used.

The passenger receipt was observed through native Account navigation at
19:23 UTC with the pending-cash explanation. Earlier receipt searches failed
because the harness searched the booking panel and retained scroll position;
correcting navigation and returning to the Account header yielded the receipt.
Do not label those searches as proof that the product lacks a receipt. Keep one
accessibility interaction sequence per emulator; concurrent dumps can interfere
with the Android test instrument and do not provide reliable failure evidence.

The subsequent driver cash-control search failed before a settlement command.
At that point the backend payment remained **PENDING**. Source inspection confirmed that
`pendingCashRideId` is assigned only in the transient completion result and is
not restored by the standard driver projection. This newly evidenced GAP-010
blocker requires a backend-authoritative recovery read and visible ride/fare
context, including pending work older than the current history page. Do not
settle through an observer script, copy a local UI flag or replay completion.
Fix and rebuild, then recover this same payment for native cash confirmation,
receipt/earnings/replay checks and renewed-session behavior. Full demo acceptance
remains **0/20 (0%)** despite this new completed-ride evidence.

### 2026-10-08 — Pending-cash recovery, full regression and phone installation

The retained synthetic cohort, database and signing identity were resumed after
the workstation interruption; no reseeding, new booking or forced ride transition
was performed. The driver now recovers actual completed `CASH`/`PENDING` work
through the owner-scoped oldest-first paginated queue documented in `api.md`.
The queue is independent of recent ride history; read failure has an explicit
reload state rather than appearing as successful empty work. Selected-page
navigation survives read-only refresh and clamps a depleted final page; it is
not a local payment-status flag. Active-ride controls remain ahead of older cash
work, and pending cash is prominent before idle availability setup.

The complete guarded PostGIS/backend regression passed **1,133 tests**, with zero
failures, errors or skips. T3 metadata verifies migration `20260908_0052`, zero
residual disposable clones and revoked temporary database-cloning authority.
The local backup/restore matched all **81 tables** and removed its disposable
target and dump, without altering demo data. The six T3 evidence kinds are
complete but the phase/deployment remain unaccepted. The initial interrupted
candidate run was not green: scoped cash fixtures and lifecycle-notification
expectations were corrected without weakening schema, locking or authorization.
The clean run also did not reproduce the previous database timeout; it does not
establish a production latency diagnosis.

The frozen mobile candidate passed **316 JVM tests**, **267 Android-host tests**,
both debug APK assemblies, **110 mobile-tooling tests**, exact mobile/web API
contract checks and **620** English/French/Arabic localization keys. Both APKs
use the documented explicit `http://127.0.0.1:8000` endpoint and muted Positron
map style. Candidate SHA-256 identities:

| Role | APK SHA-256 |
| --- | --- |
| Passenger | `035b44b5e16b6557adfbae7bfd03b47b6186568773cbda227aee91d70d7b783e` |
| Driver | `72920d89788d9b3ff92f56271cb96a11b06989475770070c6f6e6e136f215ab2` |

The driver APK's actual installed hash matched before native cash checks.
At **21:40 UTC**, inspecting and dismissing the exact retained-ride confirmation
dialog left the payment and earnings unchanged. At **21:41 UTC**, explicit native
confirmation settled that existing payment: cash became `COMPLETED`, its pending
queue count changed **2 → 1**, earning count **1 → 2**, and settled driver net
**35.00 → 70.00 MAD**. Exactly one new **35.00 MAD** earning belongs to the target
ride; its immutable fare stayed **35.00 MAD**, expected driver net **35.00 MAD**,
and operator fee/allocation **0.00**. The remaining older fixture was not settled.
At **21:45 UTC**, restarting the driver app retained the one-item pending queue;
native Account earnings displayed count two and the exact target earning. These
business actions were through the native UI, not observer settlement or completion
replay. Earlier harness attempts opened the older fixture's contextual dialog,
then refused and dismissed it without confirming; observed exact-reference/card
bounds and dialog context were required before any settlement action.

Both same-candidate role APKs were then installed with `-r` on the authorized
physical Android phone, and their actual on-device hashes matched. Existing
app data was preserved and a transport-bound TCP-8000 reverse configured. The
passenger app opened its signed-out welcome. This is installation/startup
evidence only at this point, not a physical sign-in, GPS, routing, payment or
full-row acceptance claim. The local routing process was stopped when these
checks began; older provider results do not prove current device navigation.
Physical session checks and passenger settled-receipt recovery continue below
when actually evidenced. Full demo acceptance remains **0/20 (0%)**.

At **21:58 UTC**, the current passenger APK's on-device hash matched on the
owned secondary emulator. Native Account navigation displayed the retained
ride's receipt and `CASH`/`COMPLETED` payment state. Authorized reads still showed
the same immutable fare and exactly one target earning, with the settled ride
absent from the pending queue. This combines sequential passenger observation
with the recorded current driver restart/earnings check; it is not a simultaneous
two-device ride or physical-phone payment journey. An observed System UI ANR
was dismissed using its unique Wait control before receipt verification; it was
not a TaxiMobile ANR. The physical registration harness subsequently stopped at
text-field focus validation before finishing the account journey. Neither that
attempt nor installation alone is credited as UD-01 acceptance.
