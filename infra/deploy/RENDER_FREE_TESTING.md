# TaxiMobile zero-cost temporary user testing

Use [`render.free-testing.yaml`](render.free-testing.yaml) when paid staging is
not available. The Blueprint declares only resources with Render's `free` plan:

1. One public HTTPS web service running the API and all background loops.
2. One private PostgreSQL 16 database; the first migration enables PostGIS.

Routing uses FOSSGIS's public Valhalla demo under its fair-use policy. TaxiMobile
sends the identifying `X-Client-Id: taximobile.q-sio2.github` header and limits
routing calls to ten per minute. This is suitable only for a small, coordinated
test using synthetic accounts and test coordinates. Do not use it for public
launch, load testing, real passenger journeys, or sensitive personal data.

## Important free-tier behavior

* The web service sleeps after 15 minutes without HTTP or WebSocket traffic and
  can take about one minute to wake.
* Background matching and notification loops do not run while it sleeps.
* The database has no backups, is limited to 1 GB, and expires after 30 days.
* Render can restart either free resource at any time.
* Public Valhalla is rate-limited and can return `503`; it is not an SLA-backed
  routing dependency.
* FCM and CMI remain disabled. WebSockets and cash-payment testing remain usable.

## Deploy

1. Sign in to Render and connect `https://github.com/Q-SiO2/taxi`.
2. Choose **New → Blueprint**.
3. Select branch `main`.
4. Set the Blueprint path to `infra/deploy/render.free-testing.yaml`.
5. When prompted for environment values, set:
   * `TAXIMOBILE_FREE_TEST_ADMIN_EMAIL` to an email address used only for this test.
   * `TAXIMOBILE_FREE_TEST_ADMIN_PASSWORD` to a unique strong test password.
   Neither value is committed to Git. On every start the service verifies the
   same single administrator and removes the plaintext password from the API
   process environment before accepting traffic. It refuses to promote an
   existing normal account or replace a different administrator.
6. Confirm that the plan lists exactly one free web service and one free database.
   If any resource shows a price, cancel instead of applying it.
7. Apply the Blueprint and wait for the migration, guarded administrator
   bootstrap, and `/ready` health check.

The resulting API URL resembles:

```text
https://taximobile-free-test-api.onrender.com
```

Verify:

```powershell
$api = "https://<assigned-host>"
Invoke-RestMethod "$api/health"
Invoke-RestMethod "$api/ready"
Invoke-RestMethod "$api/api/v1/meta"
```

After it is healthy, rebuild the Android debug apps with:

```powershell
cd TaxiMobile
.\gradlew.bat :androidApp:assemblePassengerDebug :androidApp:assembleDriverDebug `
  -PtaximobileDebugApiBaseUrl=https://<assigned-host>
```

Delete test accounts and deliberately discard the database when testing ends.
Do not attempt to turn this topology into production by changing one setting;
use the provider-neutral production contract and private routing infrastructure.
