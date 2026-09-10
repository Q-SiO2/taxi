This is a Kotlin Multiplatform project targeting Android, iOS, Web, Desktop (JVM).

The shared UI bundles Sora, Manrope, IBM Plex Mono, and an explicit Noto Sans
Arabic fallback from the upstream Google Fonts repositories. Their Open Font License texts are packaged under
`shared/src/commonMain/composeResources/files/font-licenses/`.

Android and iOS package distinct passenger and driver launcher icons around the
same flat TaxiMobile mark; the driver variant adds a wheel badge. Android uses
role resource overlays, while iOS targets select `AppIcon` or `DriverAppIcon`.
The reproducible iOS source images can be regenerated on Windows with
`powershell -NoProfile -ExecutionPolicy Bypass -File
.\scripts\generate_ios_role_icons.ps1`; CI verifies their catalog structure and
compiles both targets on macOS.

* [/iosApp](./iosApp/iosApp) contains an iOS application. Even if you’re sharing your UI with Compose Multiplatform, you
  need this entry point for your iOS app. This is also where you should add SwiftUI code for your project.

* [/shared](./shared/src) is for code that will be shared across your Compose Multiplatform applications. It contains
  several subfolders:
    - [commonMain](./shared/src/commonMain/kotlin) is for code that’s common for all targets.
    - Other folders are for Kotlin code that will be compiled for only the platform indicated in the folder name. For
      example, if you want to use Apple’s CoreCrypto for the iOS part of your Kotlin app,
      the [iosMain](./shared/src/iosMain/kotlin) folder would be the right place for such calls. Similarly, if you want
      to edit the Desktop (JVM) specific part, the [jvmMain](./shared/src/jvmMain/kotlin)
      folder is the appropriate location.

### Running the apps

Use the run configurations provided by the run widget in your IDE's toolbar. You can also use these commands and
options:

- Android app: `./gradlew :androidApp:assembleDebug`
- Desktop app:
    - Hot reload: `./gradlew :desktopApp:hotRun --auto`
    - Standard run: `./gradlew :desktopApp:run`
- Web app:
    - Wasm target (faster, modern browsers): `./gradlew :webApp:wasmJsBrowserDevelopmentRun`
    - JS target (slower, supports older browsers): `./gradlew :webApp:jsBrowserDevelopmentRun`
- iOS app: open the [/iosApp](./iosApp) directory in Xcode and run it from there.

The web target now hosts two separate roots, neither of which is a browser copy
of the passenger/driver mobile app: the protected operations console at `/` and
the public driver applicant portal at `#/apply`. The operations console includes
city/operator creation, operator activation, service assignment, reviewed
service-area boundary, and coherent city-configuration workflows. It resolves
compatible backend versions rather than asking staff to paste raw configuration
JSON, and the backend remains authoritative for every mutation. It also includes
permission-gated city/operator tariff, operator-fee, and scheduling-surcharge
draft/review/activation tools plus fixed-route identity, direction geometry,
fare-link, review, publication, and retirement workflows; it never calculates
authoritative money in the browser. It also provides city-scoped support and
safety queues, protected case detail, controlled transitions, minimal safety
handoff, and durable overdue-alert acknowledgement without exposing restricted
safety text to support-only staff. Market-scoped platform administrators can
place/release controlled legal holds and review immutable case-minimization
evidence; erased content is never returned to the browser. The same restricted
role can use the security-incident workspace for a bounded queue, creation,
detail/timeline review, referenced append-only facts and the next valid lifecycle
transition plus one-time postmortem completion. Typed confirmation, recent MFA
and optimistic versions protect each
write; the browser does not page staff, rotate provider keys, notify users or
execute containment. The incident workspace also shows active and released
security-response, communications, operations-liaison and postmortem ownership.
Assignment accepts an exact approved responder UUID and roster/shift reference,
uses current-version typed confirmation, and does not expose staff search. A draft direction may be created before its
fare, or it may bind an unbound reviewed fare; publication remains backend-
validated. Start the local backend on
`http://127.0.0.1:8000` with exact CORS origin `http://127.0.0.1:8080`, create the
initial administrator and scoped operations grant as documented in
`../backend/README.md`, then run:

```powershell
.\gradlew.bat :webApp:jsBrowserDevelopmentRun --no-parallel
```

Open `http://127.0.0.1:8080` for operations or
`http://127.0.0.1:8080/#/apply` for applicant testing. Localhost builds resolve
`/api/v1` at port 8000; hosted builds expect `/api/v1` on the same HTTPS origin
through the deployment reverse proxy. Both surfaces keep access and refresh
tokens memory-only, so a page reload requires sign-in. Password-only operations
access is intentionally labeled local/test and production remains disabled until
MFA, step-up, secure refresh-cookie/CSRF, CSP, and deployment review are
implemented. Applicant document controls fail closed until protected storage
and scanning are configured; they never pretend a file was accepted.

### Testing on a physical Android device

The default debug endpoint, `10.0.2.2`, works only in an Android emulator. For a
USB-connected device, keep the API on the development machine and tunnel it
through ADB instead of exposing it to the Wi-Fi network:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-android-device.ps1 -Role passenger
# Or launch the separate driver application:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-android-device.ps1 -Role driver
```

The launcher refuses to continue unless the local API and PostGIS report ready, exactly one
authorized device is attached, and the reverse tunnel is active. It then builds
the selected flavor with `http://127.0.0.1:8000`, installs it, and opens it. This
prevents a physical phone from accidentally receiving an emulator-only
`10.0.2.2` build. If the same phone briefly resets its ADB transport during a
long build, the launcher waits up to 120 seconds for that exact serial and
restores the tunnel; it refuses to switch installation to another device. The
equivalent manual commands remain useful for diagnosis:

```powershell
adb reverse tcp:8000 tcp:8000
.\gradlew.bat -PtaximobileDebugApiBaseUrl=http://127.0.0.1:8000 :androidApp:assemblePassengerDebug
adb install -r androidApp/build/outputs/apk/passenger/debug/androidApp-passenger-debug.apk
```

For a repeatable registration/login acceptance run, use the guarded smoke mode:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-android-device.ps1 `
  -Role passenger -RegistrationSmoke -ConfirmClearAppData `
  -EvidencePath .\build\t4-android-passenger-registration.json
```

This explicitly clears only the selected installed debug application's local
data, creates a unique synthetic account in the local development database,
submits the real localized Compose registration form, signs in, and waits for
the backend-authorized passenger home or driver application gate. The harness
uses Android's accessibility hierarchy entirely in memory; it does not capture
screenshots, write phone files, or print the synthetic email/password. Omit
`-ConfirmClearAppData` and the launcher fails before touching the device. Run
each role separately when both products require acceptance evidence. When
`-EvidencePath` is supplied, the new path must not exist and launch-only mode is
refused. The JSON records bounded SDK/ABI/model/locale/screen/package facts and
the two backend-confirmed journeys, but no raw device serial. It supports only
the Android-device evidence class and explicitly leaves the wider T4 matrix,
phase acceptance and deployment acceptance false.

Start the local API first. On Windows, the workspace-contained PostGIS path does
not require Docker:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\infra\scripts\setup-portable-postgis.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File ..\infra\scripts\start-portable-stack.ps1
```

To review populated and empty UI states, seed unique synthetic local accounts
before launching either role:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\infra\scripts\seed-ux-demo.ps1 -ConfirmLocalDemoData
```

The command prints the generated local-only login details and the purpose of
each account. It is additive and refuses non-development or non-loopback database
targets. Use the rich passenger and driver accounts to inspect the same en-route
ride, history, cash receipt states, inbox/support, vehicle/credential,
cooperative, earnings, and city-authorized driver surfaces; use the other
accounts for pending-driver, empty-state, and passenger fixed-route catalog and
direction review. It also creates a published Casablanca sample route, enables
the rich driver for fixed-route service, and creates a city-scoped operations
account plus a mixed application funnel so route publication, reviewer,
requirement, and suppression-aware aggregate UX can be exercised.

`setup-portable-postgis.ps1` is idempotent and needed only initially or when its
pinned runtime changes. Docker users may instead run `start-local-stack.ps1`.

`127.0.0.1` is permitted for cleartext only in debug builds; release builds need
an explicitly configured HTTPS API URL.

The passenger and driver apps use MapLibre. Debug builds default to the restrained
OpenFreeMap Positron style. If that or an injected style cannot load, the native
map switches to a bundled dependency-free neutral background while retaining
TaxiMobile route/point overlays and manual location entry. Supply another style
without changing source:

```powershell
.\gradlew :androidApp:assemblePassengerDebug `
  -PtaximobileDebugApiBaseUrl=http://127.0.0.1:8000 `
  -PtaximobileDebugMapStyleUrl=https://maps.example.test/style.json
```

A release must set both `taximobileReleaseApiBaseUrl` and
`taximobileReleaseMapStyleUrl`; the checked-in `.invalid` defaults deliberately
fail closed. The style/tile source must provide attribution and acceptable
Morocco coverage and privacy terms.

### Building Android release artifacts

Distributable Android releases require explicit HTTPS API and map-style URLs,
an explicit positive version code and semantic version name, flavor-aware
Firebase configuration, and all four signing values. Keep the keystore and its
passwords in the release secret store; do not add them to this repository or put
passwords directly in a shell command. Gradle reads them through these protected
environment properties:

```text
ORG_GRADLE_PROJECT_taximobileSigningStoreFile
ORG_GRADLE_PROJECT_taximobileSigningStorePassword
ORG_GRADLE_PROJECT_taximobileSigningKeyAlias
ORG_GRADLE_PROJECT_taximobileSigningKeyPassword
```

After those variables and the flavor-aware Firebase files are supplied, build
both applications with:

```powershell
.\gradlew :androidApp:assemblePassengerRelease :androidApp:assembleDriverRelease `
  -PtaximobileReleaseApiBaseUrl=https://api.example.ma `
  -PtaximobileReleaseMapStyleUrl=https://maps.example.ma/style.json `
  -PtaximobileVersionCode=1 `
  -PtaximobileVersionName=1.0.0 `
  -PtaximobileCrashReportingEnabled=true
```

Release builds disable backup and cleartext traffic, run fatal lint, and enable
code and resource shrinking. Retain each release's R8 mapping securely with the
matching artifact for crash deobfuscation. CI's documented
`taximobileAllowUnsignedReleaseForVerification` and
`taximobileAllowMissingFirebaseForVerification` switches exist only to verify
unsigned, non-distributable artifacts; ordinary releases reject missing signing
or Firebase configuration.

Every packaged client also sends a closed role-specific release identity. Android
uses the validated `taximobileVersionName` and version code; iOS uses
`MARKETING_VERSION` and `CURRENT_PROJECT_VERSION`; the web release reads the
strict `taximobile-client-version` and `taximobile-client-build` meta values and
the packaging script records them. On startup, native and browser products call
the command-free compatibility preflight before restoring or creating a session.
An obsolete native build shows the localized required-upgrade gate; applicant and
operations web show reload guidance. If policy cannot be checked, sign-in and
backend actions remain disabled with retry guidance. The backend independently
enforces the same policy on every v1 request and event socket, so client headers
are not an authorization mechanism.

Passenger pickup and driver location controls can request the phone's current
location. Android asks for coarse/fine foreground permission at the moment the
user selects that action; iOS asks for when-in-use authorization. The apps do not
request background location. If permission or location services are unavailable,
MapLibre tap selection and validated coordinate fields remain available.
Current-location controls admit one platform request at a time, display an
accessible loading state, and ignore repeated taps without cancelling the first
pending callback.

Passenger and driver bottom sheets share an adaptive large-text policy. At a
system font scale of `1.3×`, peek sheets open at least half-height; at `1.6×` or
greater, compact sheets open expanded and remain internally scrollable.
When a backend-authorized ride is active, Account and Inbox panels in both roles
keep its localized live status visible above their secondary content.

Transient network failures show a shared `Retry connection` action on Android
and iOS. It restores the retained secure session and reloads authoritative state;
it does not automatically replay ride, payment, location, or availability
commands whose outcome may be uncertain.
Every authenticated screen action uses the same one-shot recovery boundary: the
action executes once, an uncertain or rejected result triggers one read-only
state restore, and the original localized error remains visible over the newly
loaded backend state. Session expiry signs out instead of retaining stale data.
Before either native root launches an authenticated action coroutine, a shared
one-at-a-time gate synchronously admits it or rejects the overlapping tap. The
initiating control displays its loading spinner, all competing backend controls
remain disabled, and `finally` releases the gate after success or failure.
Only a non-error authenticated coordinator result emits a sequenced completion
event. Cash settlement and rating then render the shared 320 ms success check;
confirmed support and vehicle creation also clear their submitted local drafts.
After the app has genuinely moved to the background, its next foreground start
also performs one authoritative refresh for an authenticated session. Initial or
duplicate start events do not duplicate startup restoration.

Passenger and driver account surfaces keep ordinary support and safety separate.
Safety reports can reference the active, selected, or one of the recent
backend-authorized rides; the app sends only the ride ID, controlled category,
and description. History contains only reporter-safe status and the latest
participant-visible response. It cannot display internal notes, priority,
responder identity, reported-user identity, or the submitted description because
those fields are absent from the mobile domain model. English, French, and Arabic
all state that TaxiMobile reporting is not an emergency service and direct a
person in immediate danger to move to a safe place and contact local emergency
services. The section uses standard controls when optional safety artwork is
missing.

### Cash and manual-transfer testing

The fare estimate supplies the payment methods the passenger may select. Cash is
always available. `MANUAL_TRANSFER` appears only when the connected backend
resolves the ride's exact active city/operator/service capability and its verified
recipient plus bank account and/or M-Wallet destination. The app never invents
that capability locally or reuses methods from another city/operator.

After a transfer ride completes, the receipt shows the immutable recipient,
destination, amount/currency, and backend-issued `TM-...` reference. The optional
payer reference accepts 3–80 ASCII letters/digits or `.`, `_`, `/`, `-` after
trimming. Submitting it changes authoritative state to `PROCESSING`; the app says
operator review is pending and does not show payment success. Only backend admin
reconciliation can return `COMPLETED`. The app never asks for card data, banking
credentials, wallet PINs, OTPs, or screenshots. If transfer instructions are
unavailable, it shows an actionable error instead of substituting current
configuration.

When the receipt API includes confirmed refunds, the app keeps the original fare
visible and displays the backend's refunded total, net paid amount, and localized
reason rows. A full `REFUNDED` payment is not presented as an unverified transfer
or another instruction to send money. Settlement evidence, private operator
notes, and administrator identity are intentionally absent from mobile models.

### Crash/error monitoring

Firebase Crashlytics is linked without Firebase Analytics for Android and iOS.
Debug builds and providerless CI artifacts explicitly disable collection. A
distributable release must explicitly enable collection, use the role- and
environment-matching Firebase configuration, and retain/upload symbols: Android's
Crashlytics Gradle plugin uploads the matching R8 mapping, while the final iOS
build phase uploads the dSYM through the pinned Firebase Apple package.

TaxiMobile does not set Crashlytics user IDs, custom business keys, coordinates,
ride/payment fields, or Analytics breadcrumbs. Before enabling a public build,
approve the processor terms, data region/retention/access policy, incident owner,
and privacy notice. Force one controlled test crash in each passenger/driver
staging app and confirm that the event is isolated to the correct Firebase app and
is symbolicated. Never force a test crash in production.

Crashlytics and FCM are both no-cost Firebase Spark-plan products. TaxiMobile
does not require Firestore, Realtime Database, Cloud Functions, Storage, Hosting,
phone authentication, or Firebase Analytics; enabling one requires a separate
cost/privacy/architecture decision.

### Firebase Cloud Messaging setup

Android builds without Firebase configuration remain usable with foreground
WebSocket refresh. To enable FCM, register both application IDs
(`ma.taximobile.passenger` and `ma.taximobile.driver`) in the appropriate Firebase
environment and place its flavor-aware `google-services.json` under the Android
app module as described by Firebase. These files are ignored by source control.

For iOS, add each bundle ID to the Firebase project, place the corresponding
ignored `GoogleService-Info.plist` at
`iosApp/Configuration/Firebase/PASSENGER/GoogleService-Info.plist` or
`iosApp/Configuration/Firebase/DRIVER/GoogleService-Info.plist`, and upload the
APNs authentication key in Firebase. The build verifies that the plist bundle ID
matches `ma.taximobile.passenger` or `ma.taximobile.driver`, then installs only
that target's file. The project links Firebase Messaging, declares the production
or development APNs entitlement, enables the remote-notification background mode,
opts both native SDKs into Firebase Installation ID registration, and forwards
FID registration/rotation to the authenticated TaxiMobile device endpoint.
Installation IDs issued before authentication are retained only in process memory and
retried after login or session restore. Normal logout revokes the current
account's device registration before clearing the secure session; registering
the same installation under another account transfers its single backend owner.

The iOS project pins Firebase Apple SDK `12.17.0`. FID registration requires
Firebase Apple SDK `12.16.0` or later and Xcode `26.2` or later; CI selects that
toolchain explicitly so an older package resolution cannot omit the registration
callbacks used by TaxiMobile.

Distributable iOS Release builds also require explicit HTTPS API/map values,
positive numeric version settings, code signing, and a development team. For
example:

```sh
xcodebuild archive -project iosApp/iosApp.xcodeproj \
  -scheme "TaxiMobile Passenger" -configuration Release \
  -destination 'generic/platform=iOS' \
  TAXIMOBILE_API_BASE_URL=https://api.example.ma \
  TAXIMOBILE_MAP_STYLE_URL=https://maps.example.ma/style.json \
  TAXIMOBILE_RELEASE_VERSION_CODE=1 \
  TAXIMOBILE_RELEASE_VERSION_NAME=1.0.0 \
  TAXIMOBILE_CRASH_REPORTING_ENABLED=YES \
  DEVELOPMENT_TEAM=YOUR_APPLE_TEAM_ID
```

Repeat with the driver scheme for its distinct application. The
`TAXIMOBILE_ALLOW_UNSIGNED_RELEASE_FOR_VERIFICATION` and
`TAXIMOBILE_ALLOW_MISSING_FIREBASE_FOR_VERIFICATION` settings are CI-only; they
produce non-distributable simulator artifacts. The checked-in `.invalid` URLs
and zero release build number deliberately fail Release validation.

### Running tests

Use the run button in your IDE's editor gutter, or run tests using Gradle tasks:

- Localization catalogs/static UI copy: `..\.tools\python312\python.exe scripts\validate_localization.py`
- Portable script contract tests (including localization): `..\.tools\python312\python.exe -m unittest discover -s scripts/tests -p "test_*.py"`
- Static web compatibility runtime scenarios: `node scripts/test-web-compatibility-loader.mjs`
- Crash-reporting source gate: `..\.tools\python312\python.exe scripts\validate_mobile_crash_reporting.py`
- Connectivity/foreground/command/double-submit source gate: `..\.tools\python312\python.exe scripts\validate_mobile_recovery.py`
- Native MapLibre style-composition source gate: `..\.tools\python312\python.exe scripts\validate_maplibre_composition.py`
- Mobile/backend route-method drift gate (run from `backend/` with its environment): `python ..\infra\scripts\validate_mobile_api_contract.py`
- Operations-web/backend route-method and versioned-URL drift gate (run from `backend/` with its environment): `python ..\infra\scripts\validate_web_api_contract.py`
- Android tests: `./gradlew :shared:testAndroidHostTest`
- Android release artifact metadata: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-android-release-artifacts.ps1 -ExpectedVersionCode <code> -ExpectedVersionName <version> -ManifestPath <new-output.json>`. The generated manifest is explicitly non-distributable and records SHA-256, size, package, role, version, and the unaccepted signing/provider/device limitations of these verification builds.
- iOS simulator artifact metadata: `python scripts/generate_ios_verification_manifest.py --products-dir <Release-iphonesimulator> --expected-version-code <code> --expected-version-name <version> --output <new-output.json>`. It validates both role bundle IDs, versions, executables, and deterministic bundle hashes while explicitly refusing App Store or device claims.
- Desktop tests: `./gradlew :shared:jvmTest`
- Web tests:
    - Wasm target: `./gradlew :shared:wasmJsTest`
    - JS target: `./gradlew :shared:jsTest`
- iOS tests: `./gradlew :shared:iosSimulatorArm64Test`

---

Learn more about [Kotlin Multiplatform](https://www.jetbrains.com/help/kotlin-multiplatform-dev/get-started.html),
[Compose Multiplatform](https://github.com/JetBrains/compose-multiplatform/#compose-multiplatform),
[Kotlin/Wasm](https://kotl.in/wasm/)…

We would appreciate your feedback on Compose/Web and Kotlin/Wasm in the public Slack
channel [#compose-web](https://slack-chats.kotlinlang.org/c/compose-web). If you face any issues, please report them
on [YouTrack](https://youtrack.jetbrains.com/newIssue?project=CMP).
