# TaxiMobile — Independent feasibility, architecture and delivery audit

**Assessment date: 11 October 2026.** Repository: `C:/Users/Q/Projects`. Git HEAD: `2835c8aa7f5e97a17afcdbe647fe589cbd0421e1`, plus the existing working tree. Assessment only: no application edits, migrations, deployments, purchases or operational account changes.

## A. Executive verdict

**Keep the Python/FastAPI backend and Kotlin Compose Multiplatform mobile applications. Finish a deliberately bounded, licensed-taxi product before considering a frontend migration.** Keep the existing operations/applicant web application for the pilot; consider React for a later, independently justified web redesign. Do not replace the driver application with a browser/PWA.

The project is technically realistic. It is considerably beyond scaffolding: authoritative ride transactions, matching, driver eligibility, financial snapshots, session recovery, operations controls, native adapters and role-specific interfaces exist. Fresh local checks in this audit passed 986 backend unit/API tests, 316 shared JVM tests, both Android role compiles, 110 mobile-script tests and 266 infrastructure-script tests. These are substantial engineering assets, not proof that the transport service is ready to operate.

**Maturity: advanced implementation and internal rehearsal; not an accepted live pilot or public release.** A reasonable source-completeness estimate is approximately **80%, with a 75–85% judgment range**, using the explicit scope rubric below. Deployable completion cannot responsibly be summarized by the same number: the repository still records **0/19 P0 gates as deployment-accepted**. That is a documentary closure measure, not a claim that no useful software works or that every gate needs building from scratch.

The three largest engineering problems are:

1. **Driver location correctness and real-device service continuity.** Android observation age is discarded and replaced with transmission time; the intentionally foreground-only location policy remains unaccepted in real shifts. Push, reconnect and navigation need device/provider validation together.
2. **Missing identity/privacy lifecycle and financial-operational closure.** Verified contact delivery, deletion/export and cross-store retention are incomplete. Cash records work in source, but cash reconciliation and any operator-held money need accountable procedures; earnings are not a payout ledger.
3. **The gap between broad source coverage and a coherent, tested release experience.** Large state/screens, accessibility defects, uncommitted changes, incomplete iOS native test execution and unaccepted hosting/provider/device evidence undermine release confidence.

Visual shortcomings are primarily **design execution, hierarchy and integration problems**, not evidence that Compose cannot produce excellent UI. There is a concrete low-contrast token usage, too much secondary information in the booking/driver screens, and substantial manually wired screen state. Compose and its map-library integration do impose real platform maintenance costs; React Native also requires native integration and field testing.

**Preferred delivery path:** one authorized Moroccan city/operator, licensed drivers, one legally approved service/fare model, cash paid directly to the driver, staffed support, Android-first pilot if the cohort permits, iOS verified separately before inclusion. Preserve the existing national architecture while disabling services outside the pilot. Use managed PostgreSQL/PostGIS and an always-on API/worker; select hosting only after data-transfer and document-storage decisions.

**Planning baseline:** with two experienced full-time engineers, part-time product design and QA, allow **12–20 engineering calendar weeks to an authorized pilot candidate**, and **22–36 weeks total to a polished first-city Android/iOS public-release candidate**. These are work-package estimates, not measured velocity predictions. External approvals can delay or prevent launch independently. See the roadmap for scenarios, effort and gates.

Confidence is high in the recommendation against a full rewrite and in the identified source defects; moderate in overall completeness and delivery estimates; limited for real-world performance, iOS runtime quality and legal authorization because the necessary field/authority evidence was not available.

## B. Scope, verification and codebase findings

### Evidence boundaries

This was a repository-wide inventory plus targeted implementation review, not a line-by-line security audit. It covered documentation, Git history, application roots, core services, migrations, tests, client gateways/coordinators, native adapters, UI/theme/assets, workers, CI and deployment files. Existing Engram/project notes guided discovery; current code and Git took precedence.

The inventory found **1,094 tracked/untracked nonignored files**: 429 client, 437 backend, 108 infrastructure, 83 assets, 32 docs, two GitHub files and three root files. Source counts were approximately 48,159 Python lines under `backend/src/`, 14,536 Kotlin lines under shared `commonMain`, and 16,382 Kotlin lines under web `webMain`. Counts include comments and formatting; they do not measure quality or completion.

At inspection, Git reported **109 status entries**, including untracked directories; the tracked diff alone contained 68 changed files, 2,696 insertions and 372 deletions. An entry is not necessarily one file. No existing work was reverted, committed or staged. These results describe the working tree, not a reproducible release at HEAD alone.

The main normative references were `docs/product.md`, `architecture.md`, `design.md`, `ui.md`, `auth.md`, `pricing.md`, `payments.md`, `database.md`, `security.md`, `operations.md`, `roadmap.md`, `gaps.md`, `readiness.md`, `workflow.md` and `union_demo.md`. Country is explicitly Morocco. Casablanca appears in synthetic rehearsal data; that does **not** establish an authorized first launch city.

### Fresh checks

| Check | Result in this audit | What it establishes / does not establish |
|---|---|---|
| Backend: `.venv/Scripts/python.exe -m pytest tests/unit tests/api --junitxml=build/audit-20261011-backend.xml`, from backend | **986 passed**, one Starlette/httpx deprecation warning, 200.25 seconds | Unit/API behavior under the suite's fixtures. Does not establish fresh PostGIS transaction/concurrency correctness. |
| Shared: `:shared:jvmTest --rerun --offline --no-parallel --console=plain` | **316 tests**, 65 XML suites, zero failures/errors/skips; task actually rerun | Shared logic and JVM UI tests. JVM map implementation is a placeholder, so this is not native MapLibre rendering evidence. |
| Android: `:androidApp:compilePassengerDebugKotlin :androidApp:compileDriverDebugKotlin` | **Passed**, both role tasks executed | Kotlin compilation; not signing, package/store acceptance or physical-device tests. |
| Mobile script unittest discovery | **110 passed** | Includes deliberately rejected signing/device/evidence fixtures; their printed error messages are expected tests, not suite failures. |
| Infrastructure script unittest discovery | **266 passed** | Validator/launcher/provenance logic; not actual backup restoration, cloud configuration or human drill acceptance. |
| Mobile contract validator | **84 HTTP operations + 1 WebSocket passed** | Source contract agreement, not end-to-end service delivery. |
| Web contract validator | **112 HTTP operations passed** | Source contract agreement, not browser journeys. |
| Documentation validator | **Passed**, migration head `20260908_0052` | Links and structural consistency. It does not detect all semantic staleness; examples below. |
| JS/Wasm browser tests | See final verification addendum below | Offline attempt failed at dependency resolution. No success is inferred from older reports. |
| Fresh PostGIS tests/migrations | **Not run** | The documented full runner recreates a test database and applies migrations. The request explicitly prohibited initiating migrations. Existing reports remain historical evidence only. |
| Retained PostGIS evidence inspected, not executed here | 8 October full report: **1,133 tests, zero failures**. 11 October focused offer-location report: **90 tests, two failures** | The newer focused run is not green; F11 identifies failures still supported by current source/environment. Neither report certifies this audit's exact candidate. |
| iOS | **Not run on this Windows host** | macOS/Xcode, signing and device tests remain separate gates. CI source was inspected, not a fresh remote run. |

The first Gradle attempt pointed JAVA_HOME at the parent JDK folder and failed before building. Correcting it to `.tools/jdk21/zulu21.50.19-ca-fx-jdk21.0.11-win_x64` allowed the build. Gradle used the existing `.tools/gradle-home` and Android SDK. An initial JVM task was up-to-date; the separate forced rerun above avoids treating cache reuse as fresh execution.

The actual existing backend virtualenv uses Python **3.14.4**; the CI definition uses Python **3.12** and the package permits Python >=3.12. Local success on that virtualenv is not an independent rerun of the CI interpreter/dependency combination.

Backend report: [fresh JUnit](C:/Users/Q/Projects/backend/build/audit-20261011-backend.xml). Shared reports: [JVM report](C:/Users/Q/Projects/TaxiMobile/shared/build/reports/tests/jvmTest/index.html). These generated files are local evidence and may be overwritten by later builds.

### Progress matrix

In the table, backend paths begin at `C:/Users/Q/Projects/backend/src/taximobile_api/`; client paths begin at `C:/Users/Q/Projects/TaxiMobile/`. “Implemented” means traced source and meaningful tests, with freshness limited by the check table above.

| Component | Implementation status | Evidence | Production readiness | Remaining work | Risk |
|---|---|---|---|---|---|
| Architecture / integration | Substantial modular monolith and shared clients | `main.py`, `api/v1/router.py`; shared `data/`, `MobileAppCoordinator.kt`; passing contract checks | Coherent source, no accepted environment | Reproducible candidate, hosted integration, reduce state coupling | Medium |
| Authentication / roles | Registration, Argon2 passwords, JWT sessions, refresh rotation, revocation, offline recovery; separate staff sessions/MFA | `domains/auth/security.py`, `router.py`; `domains/administration/`; shared auth coordinators | Partial | Contact ownership/delivery, tested recovery, abuse controls, provider/device acceptance | High |
| Driver onboarding | Vehicle, credentials, applications, city authorization; protected document workflow | `domains/drivers/`, `driver_applications/`, `integrations/driver_documents.py`; mobile onboarding and web applicant | Source complete in broad scope | Verify actual licensing, expiry operations, malware scanner/private storage and insurance | High |
| Rider booking | Places, pickup/destination, quote, request/cancel and history | `domains/rides/router.py`; shared `feature/passenger/PassengerHome.kt`, Ktor gateways | Substantial, not field-accepted | Finish polished journey, address quality, stale/offline recovery acceptance | High |
| Matching / acceptance | Private offers, server locks and eligibility; current source adds acceptance-location guard | `domains/matching/service.py:222`; `domains/rides/service.py:353`; integration tests | Strong source, current DB changes not rerun here | Fresh PostGIS races, expiry/fairness/load, deployment evidence | High |
| Ride state / coordination | Server transitions, cancellation, completion, six closed coordination signals | `domains/rides/service.py`; `domains/ride_communications/`; lifecycle tests | Substantial | Device-to-device journey, lost hint/restart recovery, operational escalation | High |
| Location | Foreground repeated one-shot observations; assigned rider gets last-known position | `AndroidCurrentLocationRequester.kt:86`; `IosCurrentLocationRequester.kt`; `ForegroundDriverLocationPolicy.kt` | **Not ready for reliable continuous tracking claim** | Preserve observation age/accuracy; approve foreground operating model or implement bounded background design | Critical |
| Maps / places / routing | Native MapLibre; Valhalla/GraphHopper adapters; Nominatim adapter | shared platform `feature/maps/`; `integrations/routing/factory.py`, `integrations/geocoding/` | Adapters exist, supply/data quality unaccepted | Licensed tiles/style/geocoder, Arabic/French benchmark, legal routes and navigation behavior | High |
| Pricing | Versioned fixed tariff/economics and immutable snapshots | `domains/pricing/service.py:51`, `:253`; `docs/pricing.md` | Technically implemented for supported model | Determine legally permitted tariff/meter treatment and approved fee policy | Critical if local rule differs |
| Payments | Cash and reviewed external-transfer claims; pending cash recovery in working tree | `domains/payments/`; integration `test_pending_cash_recovery.py` | Partial financial operations | Real reconciliation/refund controls; payout accounting if holding/allocating money | High |
| Real-time / push | Transactional outbox, Postgres fanout, authorized sockets, FCM adapter and mobile relays | `core/live_events.py`, `workers/outbox.py`; `LiveUpdateSubscription.kt` | Substantial mechanisms, unaccepted delivery | Real FCM/APNs credentials, device expiry/dedup/reconnect, listener recovery across replicas | High |
| Fixed routes / scheduled booking | Broad implemented source and tests | `domains/fixed_routes/`, `scheduled_bookings/`; client forms | Not a reason to enlarge first pilot | Disable until service-specific tariff, supply, punctuality and fallback acceptance | Medium–high |
| Operations / support / safety | Scope, reviews, case handling, incident responsibilities, national city control | web `operations/`; backend administration, case and safety domains | Source-rich, staffing unproved | Real roster, duties, support drills, browser E2E | High |
| Privacy / data lifecycle | Bounded disclosures and some retention/holds; missing full rights workflow | `docs/auth.md:18`; `docs/gaps.md` GAP-021/030 | Incomplete | In-app deletion, external deletion route, export/access, cross-store erasure and retention policy | High |
| UI / accessibility | Theme, assets, localized strings, RTL direction, sheets and UI tests | shared `feature/ui/`; source and screenshot diagnosis below | Visually uneven, not approved | Contrast, hierarchy, Arabic font application, screen-reader/large-text/device matrix | High |
| Database | PostGIS, Alembic chain through 0052, constraints and transactional design | `backend/migrations/versions/`; 0048 active-ride uniqueness | Sound design; hosted reliability unaccepted | Fresh chain/restore, least privilege, capacity and actual backup/failover drill | High |
| CI / distribution / operations | Extensive CI, release identity guards, blueprints, metrics and scripts | `.github/workflows/ci.yml`; `infra/deploy/`; `TaxiMobile/scripts/` | Build infrastructure exists; no current release acceptance | Sign/review exact artifacts; iOS tests; TLS/DNS, secrets, providers, monitoring and restore | High |

### Severity-ranked findings

**F1 — P0 engineering: GPS acquisition age is not preserved.**

[AndroidCurrentLocationRequester.kt:86](C:/Users/Q/Projects/TaxiMobile/androidApp/src/main/kotlin/org/example/taximobile/AndroidCurrentLocationRequester.kt:86) accepts cached fixes up to 120 seconds old. At line 136 it converts a Location into latitude/longitude only. [MobileAppCoordinator.kt:527](C:/Users/Q/Projects/TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/MobileAppCoordinator.kt:527) submits `Clock.System.now()` as the observation time. A 119-second-old coordinate can therefore be submitted as new, defeating a 30-second location freshness check. iOS also strips the CLLocation timestamp in its coordinate conversion. This is established by source tracing, not a newly executed physical GPS reproduction. Carry acquisition timestamp/age, horizontal accuracy and a clearly defined validity policy through native/shared/network boundaries; test cached, future, delayed and permission-loss observations. Server timestamps still matter for receipt and anti-abuse; neither client timestamps nor their absence prove a trustworthy fix.

**F2 — P0 product/operational gate: foreground-only tracking is a deliberate, unaccepted constraint.**

The driver policy samples approximately every 15 seconds while available/offered and 10 seconds during a ride, plus completion spacing; it disarms when backgrounded/disconnected. Android has no location foreground service/background permission; iOS declares remote notifications, not background location. This agrees with GAP-007. It is not evidence of a Compose limitation or a forgotten service to add casually. Field-test a mounted, foreground workflow including navigation, calls, lock, permissions, heat and battery. If it fails the agreed service target, get the bounded background policy approved and implement native adapters within the present architecture. Expo would face the same OS constraints. [Android background location](https://developer.android.com/develop/sensors-and-location/location/background), [Expo location](https://docs.expo.dev/versions/latest/sdk/location/).

**F3 — P1 engineering; public-store blocker: account lifecycle is incomplete.**

`docs/auth.md` explicitly lists missing verified contact ownership, delivery reset, deletion and export. Auth router/session deletion is session revocation, not account deletion. Do not mistake suspension or retained safety cases for a complete privacy workflow. Implement deletion initiation, scoped retained-data explanations and backend processing; provide the external web request path required by Google. Apple requires in-app account deletion for account-creating apps; Google requires an in-app path and a web resource. [Apple §5.1.1](https://developer.apple.com/app-store/review/guidelines/), [Google deletion policy](https://support.google.com/googleplay/android-developer/answer/13327111).

**F4 — P1 quality: yellow text on white fails ordinary readable-text contrast.**

[TaxiColors.kt](C:/Users/Q/Projects/TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/theme/TaxiColors.kt) sets Material primary to `#D6A800`. [PassengerHome.kt:527](C:/Users/Q/Projects/TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:527) uses default TextButton styling on white toolbar surfaces. The contrast calculation for those colors is **2.22:1**, below both 4.5:1 ordinary-text and 3:1 large-text WCAG AA thresholds. Screenshots corroborate this usage. Keep gold for filled accents with dark text; use a suitably dark text token on white. This is a token/application defect, not a framework defect. [WCAG contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

**F5 — P1 platform verification: iOS test exclusion has an outdated upstream rationale.**

[ci.yml:736](C:/Users/Q/Projects/.github/workflows/ci.yml:736) states that native test binaries are not linked/executed because MapLibre Compose 0.14.0 has an absolute-path problem. The dependency remains pinned to 0.14.0. Upstream [issue #824](https://github.com/maplibre/maplibre-compose/issues/824) is closed, with a maintainer pointing to [PR #985](https://github.com/maplibre/maplibre-compose/pull/985) on 20 August 2026. This does **not** prove the pinned version is repaired or that an upgrade is compatible. It means the exception should be revalidated on macOS instead of being treated as an indefinitely unavoidable framework restriction. Simulator application links do not execute the Kotlin native tests.

**F6 — P1 release integrity/documentation: current work is not the previously verified candidate.**

The broad working-tree diff means older green CI at `168c350`/`de69829` cannot certify this source. `docs/gaps.md:688` still says immediate acceptance lacks a freshness guard, but [service.py:353](C:/Users/Q/Projects/backend/src/taximobile_api/domains/rides/service.py:353) now calls the new `domains/drivers/offer_location.py` under the established lock order. New unit tests passed in this audit; new PostGIS cases exist but were not rerun here. Update that particular claim after candidate verification. The successful docs validator establishes structure, not semantic truth.

**F7 — P1 deployment architecture: protected documents need an actual shared durable boundary.**

`integrations/driver_documents.py:142` is a local-volume adapter with AES-GCM encryption and ClamAV scanning. Its existence is positive. It is not automatically usable across independently scheduled API and retention-worker containers on a PaaS. The Render staging blueprint primarily provisions API/worker/routing/database; it is not a complete accepted document-service topology. Decide a compatible private shared store/service, test scoped reads, deletion, malware rejection, key recovery and backups, and account for regional transfer. Do not simply enable horizontal API scaling around local files.

**F8 — P1 legal/product dependency: fixed pricing is not a certified taximeter.**

The executable `fixed_fare_amount` requires `PricingModel.FIXED`; quote economics are versioned and frozen. This is valid within the implemented contract but cannot establish that fixed fares or booking/operator surcharges are lawful for the chosen city's taxi class. If local rules require meter finalization, change the approved fare/receipt workflow before field release. Do not sell distance-based taximeter functionality based on the existence of routing distance or enum values.

**F9 — P2 maintainability/quality: screen and coordinator concentration slows polish.**

`PassengerHome.kt` is 1,655 lines; `DriverHome.kt` 1,382; `MobileAppCoordinator.kt` 1,411; web `OperationsCoordinator.kt` 2,226. `App.kt` forwards many callbacks through role screens. Size alone is not a bug, but source shows many unrelated panels, action eligibility and forms living together. Extract journey/state boundaries when editing those journeys; keep tested gateways and domain rules. A migration which recreates the same orchestration in TypeScript merely relocates this cost.

**F10 — P1 localization quality: Arabic font exists but is not the general mobile typography.**

`TaxiTypography.kt:22` declares Noto Sans Arabic; `taxiTypography()` selects Sora/Manrope for general styles and `TaxiTheme.kt` does not choose fonts by locale. The only explicit caller of the Arabic helper found in Kotlin source was an operations-web field. Mobile RTL direction and translations exist, so this is not a claim that Arabic fails to render; it is a gap in predictable typography across platform fallbacks. Validate and apply the intended Arabic family/metrics and bidi handling throughout the actual mobile journey.

**F11 — P1 verification: new PostGIS location tests have unresolved fixture failures.**

The retained report `.tools/demo/offer-location-focused-20261011-130026.xml` contains 90 tests with two failures, not a passing acceptance record. In [test_immediate_offer_location.py:78](C:/Users/Q/Projects/backend/tests/integration/test_immediate_offer_location.py:78), the inactive-area fixture uses `ServiceAreaStatus.RETIRED`, but the current enum has `REPLACED` and no `RETIRED`. The future-location fixture copies a database-loaded geometry value into a new geography row; its recorded failure requires GeoAlchemy2's optional Shapely dependency, absent from the inspected virtualenv. These fail before proving the intended acceptance assertion; they are fixture/environment problems, not evidence that production accepts an invalid offer. Fix the fixtures using established supported geometry/state construction, then run the actual migrated tests. This audit did not change fixtures, install Shapely or rerun migrations. The older `.tools/demo/cash-recovery-20261008-full-tests.xml` reports 1,133 passing tests and cannot erase these later failures.

### What is genuinely built, mocked or only planned

The API routes are wired into the application factory; gateways issue real HTTP operations. The backend is not merely an in-memory demo. It contains row locks, current eligibility checks, Decimal financial arithmetic, snapshots, idempotency mechanisms and a database uniqueness constraint against multiple active rides per driver (migration 0048). Automated PostGIS lifecycle/concurrency suites exist, with older execution records. Those strengths justify retention, while a fresh database run remains necessary for the current candidate.

Native mobile maps are real MapLibre implementations; the **JVM map is explicitly a placeholder**. Synthetic demo people, route fixtures, fares and documents are rehearsal data, not provider or regulatory acceptance. Real routing/push/document adapters exist but need configured services. Cash settlement is a server-authorized record, not independent proof that cash changed hands. Manual transfer is a claim/review workflow, not an integrated payment gateway. Cards and automated mobile-payment values are reserved/deferred. A general free-text chat or masked calling service is not the current coordination product. Background tracking, self-service deletion/export, verified contact delivery and payout ledger are not completed features.

### Completion estimate and Git progression

Independent rubric: score each area 0 absent, 1 scaffold, 2 material but missing a major required path, 3 core implemented with material integration/quality gaps, 4 core path plus meaningful boundary tests. Scores evaluate implementation, not production acceptance. Weights sum to 100; `sum(weight × score / 4)` yields **78.5%**, rounded to approximately 80% because ratings are judgments.

| Area | Weight | Score / 4 | Weighted contribution |
|---|---:|---:|---:|
| Identity/recovery | 10 | 3 | 7.5 |
| Driver eligibility/onboarding | 10 | 4 | 10 |
| Ride lifecycle/matching | 20 | 4 | 20 |
| Pricing/payment records | 12 | 3 | 9 |
| Mobile journeys/UX | 15 | 3 | 11.25 |
| Location/maps/realtime delivery | 12 | 2 | 6 |
| Operations/support | 8 | 3 | 6 |
| Privacy lifecycle | 5 | 2 | 2.5 |
| Delivery/reliability tooling | 7 | 3 | 5.25 |
| Extended scheduling/routes | 1 | 4 | 1 |
| **Total** | **100** | | **78.5** |

The arithmetic total is **78.5%, rounded to approximately 80%**; use 75–85% as sensitivity, not a statistical confidence interval. The older `docs/readiness.md` 84% uses different weights and a source-oriented scope; it is not “84% of launch effort finished.” This audit deliberately weights mobile delivery/location higher and extended features lower. Broad backend source coverage is the strongest asset. Mobile source is substantial but physical product acceptance is materially behind it. Neither test count nor file count was used as the completion denominator.

Git contains 35 commits across nine dates from 20 August to 2 October. The initial implementation and a large 9 September core commit are followed by a concentration of hardening: iOS interop/Keychain/linking (27–28 September), environment/DB/maps evidence, dependency advisories, location/session recovery, R8 and APK/signing checks. This shows genuine progression and recurring integration/release friction. It does not show a React migration or a sequence of framework reversals; no such abandoned rewrite was established. Large initial commits and uncommitted rehearsal fixes make commits/week an unreliable throughput measure. Extensive national controls and evidence machinery have been built before a field-accepted city: useful eventual infrastructure, but further expansion now offers less value than closing one complete journey.

## C. Architecture comparison

Compose Android/iOS and Kotlin Multiplatform Android/iOS are classified as stable by JetBrains; Compose Wasm web remains beta in the consulted platform table. That does not guarantee every third-party adapter. [Official stability table](https://kotlinlang.org/docs/multiplatform/supported-platforms.html), consulted 11 October 2026.

Python is not the apparent bottleneck. The current workload is dominated by database transactions, routing/network I/O and reliable delivery. Keep the modular monolith and separate worker role. Measure database contention, pool reserve, outbox lag and routing tail latency before adding services or changing languages. No fresh throughput benchmark in this audit supports a vehicles-per-second or national-scale claim.

| Criterion | A: keep Python + Compose | B: Python + React Native/Expo | C: Python + React/Next web-first | D: Compose mobile + React operations |
|---|---|---|---|---|
| Speed from this tree | Fastest credible route: finish/debug existing paths | Rebuild mobile journeys before parity | Fast for forms, poor route to full driver product | Web rewrite adds time; can be staged after pilot |
| Reuse | Backend, clients, tests, assets, native adapters | Backend/API/DB/assets/contracts; little direct Kotlin UI reuse | Backend/API/DB/assets; replace UI/state | Backend/mobile retained; replace web state/UI |
| Migration/integration risk | Low migration risk; existing platform risk | High parity/session/map/location regression risk | High product mismatch; native wrapper creates a second integration project | Moderate web auth/scope/regression risk |
| Excellent visual quality | Achievable; requires design owner and component work | Achievable; broad UI ecosystem does not provide design automatically | Excellent for responsive web | Excellent within each surface |
| Native capabilities | Kotlin/Swift adapters already present | Native modules/config plugins; development builds | Browser capabilities; hybrid needs native plugins | Same mobile capabilities as A |
| Android release | Existing two flavors; compile succeeds | New packages/config/signing/testing pipelines | PWA or hybrid package; still store requirements if packaged | Same as A |
| iOS release | macOS/Xcode/device work remains | Expo/EAS can assist builds, cannot remove OS/review/device obligations | PWA limitations or native wrapper review | Same as A |
| Web | Existing Compose operations/applicant, larger browser-compatibility burden | Separate web strategy still needed | Strongest natural web fit | Strong natural fit at cost of another frontend stack |
| GPS/background | Native implementation possible; current policy foreground only | Native background APIs subject to OS lifecycle | No dependable continuous background driver GPS | Same as A |
| Realtime/push | Existing Ktor/FCM/REST reconciliation | Reimplement client lifecycle; same backend | WebSocket foreground; Web Push/lifecycle not equivalent to native service continuity | Mobile retained; web integration rewritten |
| Maps/ecosystem | MapLibre adapter is a specific risk; native SDK interop possible | react-native-maps/MapLibre/Mapbox packages require compatibility/licensing review | Mature map JS, subject to browser lifecycle | Native + web-specific map tooling as needed |
| Navigation/motion | Compose animation/insets/state APIs; current manual orchestration | Router/navigation/Reanimated choices; integration and dependencies | DOM/CSS navigation/accessibility workflow | Two UI toolchains |
| Costs/security/maintenance | Least migration expense; one client language, broad targets | Similar infrastructure; TypeScript plus native build maintenance | Similar backend; cheapest only if scope excludes native driver needs | Similar infrastructure; additional frontend skills and auth integration |
| Scale/testing | Server design dominates; device/browser acceptance still required | Same backend limits; repeat mobile tests | Same backend limits; browser and hybrid tests | Same backend limits; repeat web tests |

React Native uses native platform components and native integrations; React/Next.js renders a browser application. They are not interchangeable for GPS, background work, notification delivery or app-store binaries. Expo location explicitly documents termination/background constraints and configuration requirements. Browser pages may freeze/discard, so a PWA is suitable for applicant/admin and potentially a later rider convenience surface, not the sole reliable driver runtime. [React Native components](https://reactnative.dev/docs/intro-react-native-components), [Expo location](https://docs.expo.dev/versions/latest/sdk/location/), [Chrome lifecycle](https://developer.chrome.com/docs/web-platform/page-lifecycle-api).

Google Maps or Mapbox could be integrated using platform SDK boundaries in Compose or React Native. Neither switch is free: evaluate Moroccan address/route quality, quotas, attribution, data mixing, offline/caching terms and SDK keys first. The existing MapLibre/Valhalla/GraphHopper architecture should not be discarded merely because its hosted data supply is unfinished. API adapters are narrow enough for a measured provider choice. Consult [Google Maps terms](https://cloud.google.com/maps-platform/terms), [Mapbox terms](https://www.mapbox.com/legal/tos) and the [Expo react-native-maps integration](https://docs.expo.dev/versions/latest/sdk/map-view/) when comparing concrete alternatives.

### Weighted decision matrix

Scores 1 poor to 5 strong, **relative to this repository and the same complete taxi scope**, not a ranking of frameworks. Formula `sum(weight × score) / 5`, maximum 100. Time and core reliability receive 55% because replacing a frontend cannot excuse unsafe dispatch; polish receives 20% because it is a primary product objective.

| Criterion | Weight | A | B | C | D |
|---|---:|---:|---:|---:|---:|
| Time to production from current state | 30 | 4 | 2 | 2 | 3 |
| Product quality / visual polish | 20 | 4 | 4 | 4 | 4 |
| Core taxi reliability / native suitability | 25 | 4 | 4 | 1 | 4 |
| Cost / operational simplicity | 10 | 4 | 3 | 4 | 3 |
| Reuse of completed work | 10 | 5 | 2 | 2 | 4 |
| Long-term maintainability / ecosystem fit | 5 | 3 | 4 | 3 | 3 |
| **Weighted score / 100** | **100** | **81** | **62** | **48** | **71** |

A wins on avoided parity work, not on guaranteed visual superiority. If the available team is excellent in React Native and cannot sustain Kotlin, increase B's delivery/maintenance score and test a representative slice before deciding. Even raising B's time score from 2 to 4 adds only 12 points; reuse and regression costs still need accounting. D is the strongest later option if browser accessibility/productivity proves a real bottleneck. No fifth full-stack replacement has a supported benefit here. A narrow native iOS map bridge is a reasonable contingency, not a new whole-product architecture.

## D. UI/UX diagnosis

### Rendered evidence and limits

Inspected retained emulator images of the passenger quote, driver completion and welcome screen, a web recruitment/review screen, and the asset catalog. Files reside under `C:/Users/Q/Projects/.tools/union-demo/1c91d885932249beb9c5163063306e29/` and `assets/asset_catalog.png`. They are historical rehearsal snapshots, not current-source visual certification. Welcome artwork and insets have changed since some images were captured.

A fresh screenshot of the connected emulator was captured without dismissing dialogs or changing its state: [current emulator image](C:/Users/Q/Projects/.tools/audit-20261011/emulator-current.png). The foreground passenger app was covered by **“System UI isn't responding.”** This is an Android System UI ANR observation, **not proof that TaxiMobile caused an app ANR**. No reliable interactive journey or frame/startup measurement could be inferred from that state. Only an emulator, not a physical phone, was attached; no iOS device was available.

### Concrete diagnosis

| Observed issue | Supporting evidence | Recommended correction |
|---|---|---|
| Map competes with oversized account/safety/inbox surfaces | Passenger quote and current emulator image; PassengerToolbar source | Compact account/inbox actions; retain immediately reachable safety action; constrain long names; preserve 48dp touch areas without making every surface visually dominant. |
| Low-contrast gold labels | Rendered toolbar plus F4 color calculation | Dark text on light surfaces; gold as fill/accent. Check all component states. |
| Booking exposes navigation/technical details | Quote image shows route maneuvers and tariff identifier; current source still renders up to three maneuvers at lines 625/770 | Quote should prioritize pickup/destination, legal fare description, ETA, payment and one booking CTA. Put detailed route/fee explanations behind disclosure. Keep operational IDs in staff/debug contexts. |
| Driver control density and disabled-state ambiguity | Historical completion screenshot; broad DriverHome action panels | Make the current operational task dominant, keep completion/payment reachable, and explain why an action is unavailable. GPS sampling must not monopolize the command gate. Current policy already adds idle spacing; verify its result on devices. |
| Generic sheets carry too many unrelated panels | Fixed 28/48/78% snaps and vertical scroll in TaxiSheet; many passenger panels | Journey-specific content, sticky primary action where appropriate, tested nested scrolling and keyboard transitions. Existing large-text/inset tests are a useful foundation. |
| Technical copy in operations | Review screenshot includes backend authority wording, internal enums, identifiers and confirmation mechanics | Preserve audit semantics while translating them into task language; show identifiers on demand and keep decision evidence accessible. |
| Arabic typography is not centrally applied | F10 source tracing | Approved locale-specific typography and bidi tests, then Arabic screen-reader/device acceptance. |
| Visual assets are stronger than their integration | Consistent navy/gold catalog; several older render/fallback variants | Select one approved asset set; verify decode/fallbacks and cropping on each platform. Do not commission a new brand system. |

The existing welcome and operations screens demonstrate capable typography, rounded components, coherent color and clear basic branding. The bottleneck is not absence of design specifications: `docs/ui.md` already specifies map-first layout, one primary action and a shared identity. The gap is applying those decisions consistently, validating them on small/large/RTL screens and assigning an accountable visual reviewer.

Compose supports custom drawing, animation and native interop. There is no measured evidence here that it prevents the target visual quality. There is also no evidence establishing smooth 60/120Hz performance, cold-start targets or low-end battery behavior. Benchmark release builds on representative hardware; avoid attributing emulator behavior or debug-build slowness to the framework.

For a fast credible improvement, use an experienced mobile product designer with a Compose implementer to approve the full rider and driver state sequence before adding more screens. Build a deterministic visual fixture gallery using existing states: sign-in, pickup, quote, matching, assigned, pickup failure, in-trip, completion, unpaid cash, offline, expired session and restricted driver. Capture English/French/Arabic, large text and keyboard states; compare implementations against approved references. Add accessibility semantics and measured contrast before decorative motion. Refactor only the components/journey boundaries touched by this work.

## E. Legal and deployment risk

All external sources below were consulted on **11 October 2026**. Legal findings distinguish official requirements, indicative materials and unanswered application-specific questions. This audit is not a Moroccan legal opinion or operating authorization.

### Morocco: what can and cannot be concluded

| Topic | Verified basis / status | Implication and required validation |
|---|---|---|
| Software development and publication | Development, store distribution and operating passenger transport are separate activities. No operating authorization for TaxiMobile was found in repository evidence. | Continue synthetic development/rehearsal. Store approval cannot substitute for local authority to operate. Publishing a booking service still entails consumer/privacy/platform obligations. |
| Taxi/platform authorization | Official Parliament question 28778 records unresolved regulatory concerns and a 9 June 2026 answer date; the visible question is not itself a grant or statutory answer. SGG's 25 May 2026 digital-news digest reproduces reporting about prior authorization. | Obtain the current applicable national/local texts and a written opinion/authority response for the exact legal entity, city and intermediation model. Do not infer a nationwide authorization or blanket ban from press summaries. [Parliament record](https://www.chambredesrepresentants.ma/ar/%D9%85%D8%B1%D8%A7%D9%82%D8%A8%D8%A9-%D8%A7%D9%84%D8%B9%D9%85%D9%84-%D8%A7%D9%84%D8%AD%D9%83%D9%88%D9%85%D9%8A/%D8%A7%D9%84%D8%A3%D8%B3%D9%80%D8%A6%D9%84%D8%A9-%D8%A7%D9%84%D9%83%D8%AA%D8%A7%D8%A8%D9%8A%D8%A9/hwl-alantshar-almtzayd-lttbyqat-nql-alashkhas-walkhdmat), [SGG digest](https://www.sgg.gov.ma/Portals/1/veille_juridique/actualite_numerique/aj_25052026.pdf). |
| Licensed-taxi dispatch model | Matches the documented cooperative product. A secondary administrative directory describes prefectural authorization for technological taxi intermediation; the precise official procedure was not independently retrieved from Idarati. | A credible strategy to validate, not a loophole. Ask prefecture/province for applicable arrêté, applicant eligibility, territorial limits, dispatch/booking restrictions, fees and approval process. Do not budget around the secondary site's stated processing time. [Directory lead, not legal authority](https://www.communesmaroc.com/fr/demarches-administratives/idarati-thematic-f3df9503-d376-4eee-be44-0d2efc9e9007/idarati-cat-44c7eb7e8108/idarati-c432c31f-0f88-4c72-9106-79744759e09e). |
| Driver/vehicle verification | The application can enforce configured documents and city authorization; it cannot establish the validity of a professional license itself. | Verify taxi operating rights, professional driver credentials, vehicle inspection, owner/driver authority, expiry and permitted service area with the competent authority. A cooperative membership alone is insufficient evidence. |
| Fare/meter/fees | No chosen city's enforceable tariff order or approval of the demo fixed fare was inspected. | Counsel/authority must settle meter finalization, fixed routes, booking surcharge, operator fee, cancellation and receipt wording. Do this before extending pricing software. |
| Personal data | CNDP publishes Law 09-08, formalities and rights guidance. Notification/authorization depends on the treatment, data and legal basis. | Identify controller/processors, lawful grounds, notice, access/rectification/opposition handling, security and bounded retention. Resolve driver ID/document and incident-data formalities specifically. [Law 09-08](https://www.cndp.ma/loi-09-08/), [CNDP notification procedures](https://www.cndp.ma/procedures-de-notification-process/). |
| Foreign hosting and processors | CNDP explains foreign-transfer conditions and form F118; underlying processing must first have approved declaration/authorization. | Frankfurt hosting, push/crash services and foreign support access require a mapped transfer assessment and applicable formalities. Consent or EU hosting should not be assumed to remove the need. [CNDP transfers](https://www.cndp.ma/transfert-de-donnees-a-letranger/). |
| Precise geolocation | Personal-data processing must have defined purposes, necessity, disclosure, access controls and retention. The exact filing/category for this cooperative model was not confirmed. | Get CNDP/legal validation of driver/passenger treatment, precision, shift boundaries, retention and rights. Do not label all location data legally “sensitive” without analyzing the statute, but treat it as high-risk operationally. |
| Insurance / passenger protection | ACAPS identifies mandatory motor civil liability under the insurance code. | Obtain written confirmation of taxi/commercial passenger use and app-dispatched trips, passenger coverage, exclusions and incident responsibilities; evaluate platform liability separately. [ACAPS](https://www.acaps.ma/fr/grand-public/biens/assurance-automobile). |
| Payments / custody | Bank Al-Maghrib publishes Law 103-12 regulating credit/payment institutions and payment services. | Cash paid directly to drivers reduces custody complexity; it does not eliminate receipts, disputes or tax duties. Have counsel/payment provider assess any pooled account, wallet, onward remittance or commission collection. Do not equate a database payment row with authority to provide regulated payment services. [BAM law](https://www.bkam.ma/fr/content/download/757666/8545663/loi%20bancaire%20fr%2022.pdf). |
| Tax / invoices / cooperative entity | The Ministry of Finance publishes the 2026 tax code; entity, fee and supplier choices are not fixed here. | Accountant must determine who invoices transport/platform fees, tax treatment, records and lawful retention. No VAT rate, exemption or legal-entity recommendation is asserted. [CGI 2026](https://www.finances.gov.ma/Publication/dgi/2025/CGI-2026-FR.pdf). |
| Maps/data licensing | Public OSM servers have usage policies independent of open-data licensing. Nominatim public service limits heavy use and disallows client-side autocomplete. | Use a contracted or controlled provider, attribution and allowed caching. A MapLibre license does not buy tiles, address quality or a routing SLA. Review alternative Google/Mapbox content terms before mixing providers. [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/), [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/). |

**Largest viability threat:** failing to obtain a workable city/operator authorization and approved fare/insurance/data arrangement, or failing to recruit enough available licensed drivers to provide dependable pickup. Neither threat is reduced by switching the UI framework. A licensed dispatch partnership is the preferred validation path because it aligns with existing supply and project purpose; formal authorization and commercial adoption must still be demonstrated.

### Store and OS gates

Both role applications need verified developer ownership, release signing custody, production identifiers and entitlements, reviewer access, accurate store descriptions/screenshots, privacy policies, data disclosures, deletion paths and permission explanations. Android target SDK is pinned to 36 in source; compliance must be checked for the actual submission date. New personal Play accounts can have additional testing/device-verification requirements. Apple organization enrollment requires legal-entity verification. Published enrollment prices are **USD 99/year for Apple** and **USD 25 once for Google Play**, subject to local terms. [Apple enrollment](https://developer.apple.com/programs/enroll/), [Google enrollment](https://support.google.com/googleplay/android-developer/answer/6112435).

If background location is approved as product scope, implement the appropriate Android service/permissions and iOS capabilities, with visible disclosure and review evidence. It is not guaranteed continuous execution after termination. Current foreground-only source avoids requesting those capabilities but must meet its narrower service promise. [Google background-location review](https://support.google.com/googleplay/android-developer/answer/9799150?hl=en-en), [Android OS guidance](https://developer.android.com/develop/sensors-and-location/location/background).

Real-world transport payments are not automatically an app-store digital-content purchase. Verify the precise payment UX under current policies; do not add in-app purchase merely because payment happens through an app. Privacy labels must include third-party SDK behavior and crash/push identifiers, not only the data your own API stores. [Apple review guidelines](https://developer.apple.com/app-store/review/guidelines/).

### Practical deployment plan and blockers

| Class | Current blocker | Concrete release evidence |
|---|---|---|
| Engineering | GPS provenance, privacy lifecycle, current DB integration, iOS native tests, mapped provider failures | Same-candidate test results and signed device journeys, including restart/offline/permission loss |
| Platform/deployment | Environment isolation, DNS/TLS, signing, FCM/APNs, mapping supply, protected storage topology | Provisioned staging/prod, restricted secrets, immutable artifacts and working provider traces |
| Operational | Real staff roster, support coverage, cash reconciliation, backups, pager and rollback | Named owners, completed drills and observed recovery within agreed bounds |
| Legal/regulatory | City/operator/tariff/insurance/CNDP arrangements | Written applicable authority and accountable legal sign-off |
| Quality | Contrast, panel density, RTL/font/keyboard issues, accessibility and performance unknown | Approved screenshots and representative device/browser task completion |

Use the existing **FastAPI API + separate worker + PostgreSQL/PostGIS**. Preserve transactional outbox and Postgres fanout; do not introduce Redis/Kafka/Kubernetes without measured need. Long-lived WebSockets and workers favor always-on containers rather than forcing the existing server into short-lived request hosting. Audit pools so each API, worker and LISTEN connection leaves database reserve. Keep health/readiness private diagnostics appropriately bounded.

Provision isolated development, staging and production secrets/data. Terminate HTTPS with a managed service, allow only intended origins/hosts, use secure staff cookies/CSRF and least-privilege database roles. Separate migration credentials from runtime. Configure production FCM/APNs for both roles, private routing, tiles/style/geocoder, malware scanning and recoverable document encryption keys. Add log/metric/crash retention and redaction, off-host alerts, a staffed response process and a tested rollback path. Restore **database plus protected documents plus necessary keys**, not just a database dump. Define RPO/RTO with the operator and measure a restore; do not invent acceptance numbers after testing.

| Hosting approach | Fit and tradeoff | Planning cost, not a provider quote |
|---|---|---|
| Managed PaaS such as the existing Render blueprint, plus managed PostGIS | Lowest initial infrastructure engineering; requires compliant region/transfer arrangement, enough memory, worker/private services and a deliberate document solution | Pilot hosting/services allowance roughly USD 150–400/month excluding SMS, staffing, legal work and substantial usage growth |
| Managed application containers + managed PostgreSQL in an approved region/provider | More networking/setup choices; useful if document/private-service topology or regional requirements exceed blueprint | Roughly USD 200–600/month for small production/staging footprint; quote exact service shape |
| Moroccan managed host / managed VPS with acceptable database and backup service | Potentially useful for residency/authority constraints; verify PostGIS, restores, patching and SLA rather than assuming “local” means compliant | Obtain quote; no verified like-for-like Moroccan offer in this audit |
| Self-managed VPS | Can reduce invoice; adds patching, database, keys, backup and on-call ownership | Server rent is only a fraction of total cost; not preferred for a small team without operations capacity |
| Free/test hosting | Useful for synthetic rehearsal only | Sleeping services, limited capacity and temporary DB offerings do not satisfy taxi availability |

Render explicitly supports PostGIS. Its official cost article describes a July 2026 USD 13 example for one smallest web service and database; that is **not** a TaxiMobile production budget. It excludes a properly sized worker/routing/scanner, storage, monitoring, second environment and reliability needs. The live pricing page did not expose a complete SKU table to the text browser, so the ranges above are engineering budget allowances, not verified current quotes. [PostGIS support](https://render.com/docs/postgresql-extensions), [Render cost structure](https://render.com/articles/how-much-does-cloud-application-hosting-cost-for-small-businesses), [current pricing](https://render.com/pricing).

Illustrative monthly pilot worksheet: API/worker USD 30–80; managed database/backups USD 30–100; maps/routing/geocoder USD 40–120; protected storage/scanning/monitoring USD 20–60; staging/egress reserve USD 30–40. Total USD 150–400. Capacity, map quotas, region and actual contracts can exceed it. A small public deployment allowance is USD 300–1,000/month before personnel and communications. These are not quotations or promises of capacity. Model SMS separately as deliveries × local provider unit price, including failed/retried verification; payment fees as transactions × contracted rate; maps as active sessions/lookups, not just completed trips. React Native does not materially lower those backend/provider costs; Next server rendering may add hosting without helping taxi dispatch.

## F. Migration cost-benefit analysis

| Asset | React Native mobile migration | React web migration |
|---|---|---|
| Python backend, PostGIS, migrations, worker business logic | Retain | Retain |
| OpenAPI contracts, authorization model, server tests | Retain; add client parity checks | Retain; preserve cookie/CSRF/scope behavior |
| Brand, approved designs, translations | Reuse with format/font/asset adaptations | Reuse with responsive/accessibility adaptations |
| Shared Kotlin domain/gateways/coordinators | Specifications and test cases reusable; TypeScript code rewrite in ordinary Expo architecture | Same for affected web/shared logic |
| Compose screens/components/semantics | Rewrite | Rewrite |
| Android/iOS storage/location/push glue | Behavior reusable; bridge/reintegrate and revalidate | Still needed for a native driver wrapper |
| Tests | Server suite retained; mobile UI/unit tests reauthored, scenarios reused | Web rendering/E2E tests reauthored |
| Release/signing/provider setup | Some account identities/assets retained; build automation adapted | Web build/auth/CSP pipeline adapted; store work persists for wrappers |

The shared mobile Kotlin production layer alone is about 14.5k lines; the web production layer about 16.4k. Those are rough rewrite surfaces, **not billable effort estimates**. The 48k-line backend source and its domain tests remain under all reasonable alternatives. Therefore it would be wrong to say “migration loses everything,” and equally wrong to promise 80–90% direct mobile code reuse. Preserving Kotlin behind a React Native bridge is possible but adds a second runtime/bridge ownership model; it is not the simplest Expo migration for this team.

Migration might pay if a measured prototype shows markedly faster accepted delivery by the actual team, or if an essential native integration cannot be repaired economically. It is not justified by unattractive screenshots or a general preference for JavaScript. A fair experiment must include secure login/refresh, map interactions, driver location policy, reconnect, cash completion and Arabic/large-text UI—not just a landing screen. No such comparative experiment was available; migration being faster is unproven.

## G. Roadmap, estimates and smallest complete product

The detailed work packages, scenarios, dependencies and acceptance gates are in [RECOMMENDED_ROADMAP.md](C:/Users/Q/Projects/RECOMMENDED_ROADMAP.md). Suggested pilot scope is a recommendation for owner approval, not an amendment to product requirements.

Minimum complete journey: rider account and recovery → manually verified licensed driver/vehicle/city eligibility → accurate pickup and destination → lawful quote or approved meter workflow → request/private offer/acceptance → authoritative arrival/trip status and limited coordination → completion → explicit cash receipt/settlement record → history, dispute and staffed support. Necessary recovery includes expiry, no supply, cancellation, weak network, process restart, rejected/stale GPS, unavailable push, denied permissions and uncertain command outcome. Privacy/deletion and emergency handling cannot be deferred merely by calling a public product an MVP.

Simplify to one service area, cash direct to driver, known cohort and operating hours; disable manual transfers unless reconciled end to end. Defer card processing, wallets, pooled seats, national rollout, advanced analytics and scheduled/fixed-route availability unless the pilot's approved service specifically requires them. If only a fixed-route model obtains legal approval, revise the pilot journey explicitly instead of pretending on-demand tariffs are authorized.

Spend the next tranche on source baseline/review, observation correctness and core journey UX; run authority/privacy/provider work in parallel; then verify on devices and in staging. Do not spend it replacing every screen or expanding national controls.

## H. Final decision — direct answers

1. **Technically realistic?** Yes, as licensed-taxi digital infrastructure with a bounded launch and genuine operating organization.
2. **How far from deployable?** Approximately 80% of defined source scope exists; live acceptance is blocked. Budget 12–20 weeks for a pilot candidate with the stated team, independent of external approval delays.
3. **Three engineering problems?** Location/device continuity; incomplete identity/privacy/financial operations; candidate/UX/platform verification fragmentation.
4. **Is Compose causing the appearance problem?** Primarily no. Specific ecosystem friction exists, but observed hierarchy, contrast and density problems are implementation/design execution.
5. **Keep, switch, web-first or hybrid?** **Keep Compose mobile and current web for the pilot.** React operations is a later selective option, not a prerequisite. Reject a browser-only driver strategy.
6. **Python?** Retain FastAPI and the modular monolith; make targeted reliability/provider changes. No rewrite or microservice case is established.
7. **Migration reuse/loss?** Retain backend/DB/contracts/assets and test scenarios; rewrite most affected Kotlin UI/state/network presentation and revalidate native glue. Do not translate source-line ratios into effort saved.
8. **Is migration faster?** Not supported by available evidence; expected slower because parity and release validation are added before the same unresolved launch gates.
9. **Largest legal/operational threat?** No validated city/operator/fare/insurance/data arrangement, compounded by unproven sufficient licensed-driver supply and response staffing.
10. **What would I do to ship?** Own one city's full operating journey, appoint a visual reviewer and an operations/legal owner, fix GPS provenance and account lifecycle, resolve providers/signing, run the same candidate through physical-device and staffed staging/field acceptance, then expand only on measured outcomes.

Reconsider mobile architecture if a time-boxed native integration investigation cannot restore critical iOS/map tests or reliable permitted location behavior, if measured release performance misses agreed targets despite focused tuning, or if the actual available team demonstrates substantially faster complete-journey delivery in React Native. Reconsider the web stack if accepted accessibility/browser requirements are persistently costly in Compose web. Reconsider the product model immediately if authorities reject its fare, territory or platform role. Those are evidence-based triggers; sunk costs alone are not a reason to retain anything.

### Final verification addendum

Browser retry results and final file-integrity checks are recorded here before delivery.
