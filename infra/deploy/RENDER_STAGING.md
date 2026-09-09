# TaxiMobile managed user-testing environment on Render

This runbook creates a non-production staging environment from the Git repository
using [`render.staging.yaml`](render.staging.yaml). GitHub stores and versions the
source; Render runs the API and private services. GitHub Pages and GitHub Actions
are not application servers and must not be used as the live TaxiMobile API.

## Resulting environment

The Blueprint provisions four resources in Frankfurt:

1. One public HTTPS FastAPI web service.
2. One private background worker for matching, outbox, credential lifecycle,
   scheduling handoff, privacy-bounded analytics refresh, case-alert paging, and
   legal-hold-aware case retention.
3. One private, disk-backed Valhalla service with a dated Morocco extract.
4. One managed PostgreSQL 16 database with no public ingress. Migration `0001`
   enables Render's supported PostGIS extension before the remaining migrations.

API and worker use the same Dockerfile but have separate process roles. Only the
API receives the generated JWT secret and public hostname. Database and routing
traffic stay on Render's private network. The Blueprint generates JWT and
monitoring secrets; it contains no credential value.

This is not a free topology. Render does not offer free private services,
background workers, or persistent disks. Review the dashboard's current monthly
estimate and billing controls before approving the Blueprint. Do not create
preview environments, because they would duplicate billable services and data.

## 1. Repository preflight

From the workspace root, run:

```powershell
.\backend\.venv\Scripts\python.exe .\infra\scripts\validate_source_credentials.py
.\backend\.venv\Scripts\python.exe -m pytest .\backend\tests\unit
```

The root `.gitignore` excludes local environments, databases, build artifacts,
Firebase files, signing keys, and other deployment secrets. Before the first
push, inspect `git status --short` and do not stage a file you do not recognize.

## 2. Put the source in a private GitHub repository

Create an empty private GitHub repository without generated starter files. Then,
from the workspace root, initialize and push only after reviewing the staged set:

```powershell
git init
git branch -M main
git add .
git status --short
git commit -m "Prepare TaxiMobile staging deployment"
git remote add origin https://github.com/<owner>/<private-repository>.git
git push -u origin main
```

Never paste a GitHub token into a command, tracked remote URL, screenshot, or
support message. Use the browser credential flow or a credential manager.

## 3. Apply the Render Blueprint

1. Sign in to Render and connect the private GitHub repository.
2. Choose **New → Blueprint**.
3. Select the repository and `main` branch.
4. Set the Blueprint path to `infra/deploy/render.staging.yaml`.
5. Supply the API's independent
   `TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY` as an unpadded base64url encoding
   of exactly 32 random bytes. Also set `TAXIMOBILE_CORS_ORIGINS` to the exact
   HTTPS operations-web origin; the operations web and API must be same-site or
   share a reverse proxy for the strict cookie.
6. Supply the worker's secret `TAXIMOBILE_CASE_PAGER_URL` (HTTPS) and an
   independent 32+ character `TAXIMOBILE_CASE_PAGER_TOKEN`. The endpoint
   must accept the minimal authenticated alert envelope documented in
   `../../docs/operations.md`; do not route it to a general logging collector.
7. Review the four resources and the estimated charge before applying.
8. Wait for the database, Valhalla graph build, migration, API, and worker to
   become healthy. The first routing build is expected to take longer than an API
   redeploy because it downloads and processes the pinned Morocco extract.

Do not make the database or Valhalla service public. Do not replace generated
secrets with memorable values. If a resource fails, inspect its deployment logs;
do not copy environment values into an issue or chat.

Cash is ready by default. To enable the single-recipient manual bank/M-Wallet
pilot, add `TAXIMOBILE_MANUAL_TRANSFER_ENABLED` and the three
`TAXIMOBILE_TRANSFER_*` settings documented in `../README.md` to the API service only, verify the
recipient and reconciliation runbook, then redeploy. Never add them to the
worker, repository, or mobile build. CMI/card processing remains deferred.

## 4. Verify the public boundary

Render assigns the API an HTTPS URL similar to:

```text
https://taximobile-staging-api.onrender.com
```

Check only the non-mutating public endpoints:

```powershell
$api = "https://<assigned-host>"
Invoke-RestMethod "$api/health"
Invoke-RestMethod "$api/ready"
Invoke-RestMethod "$api/api/v1/meta"
```

Expected states are `ok`, `ready`, and TaxiMobile API version `v1`. The worker is
private and should be checked through its Render logs/shell. Its `/ready` endpoint
requires a successful iteration from all fixed worker loops.

## 5. Bootstrap the first staging administrator

Open the API service's trusted Render shell and run:

```text
python -m taximobile_api.operations.render_entrypoint bootstrap-admin --email operator@example.com
```

The command reads the password twice from the hidden prompt. It permits only the
first administrator and never promotes an existing passenger or driver account.
Do not use a personal production password in staging.

Map the same account to the first market-scoped operations grant, then enroll
its authenticator factor from the same trusted Render shell:

```text
python -m taximobile_api.operations.render_entrypoint bootstrap-operations --email operator@example.com --market-code MA
python -m taximobile_api.operations.render_entrypoint enroll-mfa --email operator@example.com
```

The enrollment command prints the provisioning URI and recovery codes exactly
once. Keep the shell private and store recovery codes offline. For an approved
factor-loss recovery, rerun the second command with `--replace-existing`; the new
factor is confirmed before commit and all prior operations sessions are revoked.

## 6. Point Android user-testing builds at staging

After the assigned API URL is healthy, rebuild both Android variants with that
HTTPS base URL. Do not hard-code the Render host into shared source code:

```powershell
cd TaxiMobile
.\gradlew.bat :androidApp:assemblePassengerDebug :androidApp:assembleDriverDebug `
  -PtaximobileDebugApiBaseUrl=https://<assigned-host>
```

Install the generated passenger and driver APKs on separate devices or profiles.
The mobile clients connect directly over HTTPS; `adb reverse` is no longer used.

## 7. Stop or remove the environment

When the user-testing period ends, export or deliberately discard staging data,
then suspend/delete the Render Blueprint resources from the dashboard to stop
ongoing charges. Staging data is not production data and must never be copied to
production without an explicit privacy and migration review.
