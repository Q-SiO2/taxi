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
* FCM is disabled in this Blueprint because a sleeping all-in-one process is not
  a reliable background-delivery environment; FCM itself and Crashlytics are
  no-cost Spark-plan products. WebSockets remain usable while the service is
  awake.
* External overdue-case paging is intentionally disabled. Alerts remain durable
  and visible while the service is awake, but this topology must not carry a
  live safety pilot or depend on unattended response.
* The retention loop runs only while the service is awake. The expiring database
  has no backups and cannot demonstrate production legal-hold review, backup
  expiry, or restore behavior.
* CMI/card processing is deferred, not simulated. Cash works immediately.
  Manual bank/M-Wallet transfer is present but disabled until a verified pilot
  recipient and reconciliation owner are configured.

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
   existing normal account or replace a different administrator. The same
   guarded startup maps that administrator to the existing Morocco-scoped
   platform grant so the temporary operations console can be exercised; hosted
   MFA remains disabled only in this synthetic password-only topology.
6. Confirm that the plan lists exactly one free web service and one free database.
   If any resource shows a price, cancel instead of applying it.
7. Apply the Blueprint and wait for the migration, guarded administrator
   bootstrap, and `/ready` health check.

To exercise manual-transfer UI and reconciliation with controlled test data,
add these service environment values in Render and redeploy:

```text
TAXIMOBILE_MANUAL_TRANSFER_ENABLED=true
TAXIMOBILE_TRANSFER_RECIPIENT_NAME=<verified test recipient label>
TAXIMOBILE_TRANSFER_BANK_ACCOUNT=<test destination, optional with wallet>
TAXIMOBILE_TRANSFER_WALLET_ID=<test destination, optional with bank>
```

Use only one recipient in this topology. Never enter a password, PIN, OTP,
statement credential, card number, or provider secret. The passenger claim moves
the payment to `PROCESSING`; the controlled test administrator must use the
authenticated reconciliation endpoint to verify or reject it. Synthetic
verification proves UI/state wiring only and is not financial-settlement evidence.
Do not use this expiring, backup-free deployment for real fares or live money.

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
