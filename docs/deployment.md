# TaxiMobile — Railway Staging and Release Operations

## Active production-deployment goal - 23 October 2026

[The real-world execution plan](real-world-launch.md) now owns the next production
preparation packets, while this document retains deployment controls and provider
history. Start with source/evidence reconciliation and a costed, isolated target
design, backup/restore, monitoring and rollback acceptance. Do not mistake the
existing Trial staging environment for accepted sustainable production hosting.
The [latest alpha handoff](board-alpha-handoff.md) and
[applied recovery record](redesign/staging-recovery.md) supersede the old paused
deployment/credential checkpoints below. Do not repeat that cutover, upgrade
billing or delete either preserved volume without the applicable authorization.

## Current health and allowance — 20 October 2026

[Read-only staging verification](redesign/board-alpha-evidence/railway-runtime-20261020-native-rehearsal.json)
confirms five online services, one running replica each, no pending work and no
recent failures or active issues. The current PostGIS samples are approximately
0.221 GB disk / 0.221 GB memory. The
[actual trial capture](redesign/board-alpha-evidence/railway-trial-20261020.json)
shows 12 days / $2.26 remaining. These are timestamped observations, not future
availability guarantees. Both volumes and trial-only limits remain preserved;
no new hosting mutation is needed for the native callback repair. Temporary
Casablanca staff roles expire today around 11:27 UTC and are not auto-renewed.

## Final browser correction — 20 October

The current live web v8 again passes all 102 existing asset/canonical route/proxy/
security checks. A newly exercised shorthand `/apply` route returns
`302 http://alpha-web-staging.up.railway.app:8080/apply/`, which fails normal browser
entry. Canonical `https://alpha-web-staging.up.railway.app/apply/` works, including
normal applicant sign-in and submitted revision 7 readback.

The prepared [web v8 proxy-only revision](redesign/board-alpha-evidence/candidate-web-v8-proxy-r1.json)
adds `absolute_redirect off` at nginx server scope. It retains all 93 exact compiled
assets, the public manifest, CSP/private upstream and other service configuration.
Eight packaging checks pass; the new hosted redirect regression is preserved red.
Railway rejected upload with “Deploys have been paused temporarily.” Its
[status page](https://status.railway.com/) reports a platform build pause affecting
new builds, with running services unaffected. No new deployment or pending work
was created; the five current services remain healthy. Do not claim the repair
is live, upgrade billing or bypass the provider pause. Follow
[the handoff](board-alpha-handoff.md) to retry the exact packet after resumption,
then require 103 hosted checks and normal shorthand browser entry.

The original v15 native snapshot/APKs remain preserved. Only current nginx
configuration differs among its broad archived inputs; compiled native
application sources are unchanged. No native rebuild is needed for this repair.
Four extra city roles expired at 11:27 UTC; baseline recruitment access remains.

## Current recovery checkpoint — 19 October 2026

The owner declined a paid upgrade and explicitly approved a trial-only volume
swap, then applied Railway's three staged changes manually after the connector
rejected its apply call. The full original 500 MB `alpha-postgis-data` volume
`b9097b45-80a9-4964-9844-c247b08d1db5` is preserved **unattached**. Fresh 500 MB
`alpha-board-data-20261015` (`8ed86e48-25f5-4fa6-8feb-2f930ba8b547`) is attached
to the same private PostGIS service. No volume was erased and no paid plan bought.

All five services in the existing TaxiMobile Alpha staging environment are online:

| Service | Verified deployment |
| --- | --- |
| API | `e5e108a0-e5dd-4553-93fd-292026c98b63` — same backend v6 build, normal migrations after bootstrap-input cleanup; fresh readiness/proxy checks pass |
| Web | `ceee310c-e957-49ad-945d-b9f2d292eb61` — v8 board presentation and applicant Save repair; 93 assets / 29,577,316 source bytes; all 102 hosted checks pass |
| PostGIS | `10348a72-65f4-4b80-8474-e8a950ccd282` — fresh trial volume, PostGIS 3.4, migration `20260908_0052`, 81 tables |
| Worker | `8ca5a361-9b66-4d7a-8041-c9a5754bbe47` — private; matched real synthetic hosted/native offers |
| Routing | `dec657d1-e507-421d-9bc2-15f0250385b7` — private Casablanca routing; actual native route rendered |

The [web](https://alpha-web-staging.up.railway.app) and
[API](https://alpha-api-staging.up.railway.app) use HTTPS. Nginx uses the
container's numeric DNS resolver, a variable private upstream, short DNS caching
and IPv4 upstream resolution; a static resolved address had survived an API
replacement and broken proxy traffic. CSP, secure-cookie/CSRF, forwarded TLS,
WebSocket handling and private-only database/worker/routing boundaries remain.

Web v8 completed deployment on 19 October at 11:21:39 UTC.
[All 102 hosted checks](redesign/board-alpha-evidence/hosted-web-v8-20261018-oct19-first.json)
pass. Its actual profile-only applicant Save confirms revision 2, followed by UI
Submit and independent owned readback of `SUBMITTED`, revision 3. Matching review
and full visual/locale acceptance remain separate. The
[packaging-only review](redesign/board-alpha-evidence/web-v8-packaging-inputs.json)
measures fallback JS at 6,827,377 bytes (+2.90% over v7), gzip9 at 1,624,307
(+19,027). The reviewed JS ceiling is 6,900,000; loader, per-Wasm and total caps
are unchanged. Original 411 compilation inputs remain archived independently
from the changed packager. Size measurements do not prove startup performance.

Web v7 completed deployment on 18 October. Its
[102 hosted checks](redesign/board-alpha-evidence/hosted-web-v7-20261018-client-headers.json)
verify all 93 asset hashes, applicant routing, security headers and version/auth
boundaries. [Actual protected review](redesign/board-alpha-evidence/wl3-hosted-v7-protected-review.json)
covers EN/FR/AR recruitment/applicant reads, retained drafts/styles and cancelled
withdrawal. Protected writes, observed polish defects and full acceptance remain open.

Earlier web v6 completed deployment on 17 October at 09:39 UTC. Its
[98 hosted checks](redesign/board-alpha-evidence/hosted-web-v6-20261017.json) and
[fresh MFA/recovery/scope record](redesign/board-alpha-evidence/wl2-hosted-v6-session-recovery.json)
pass within their declared scope. Corrected Notepad grayscale and reachable
short-height MFA cancel are actual renders. Protected body localization,
desktop card bounds and full accessibility acceptance remain open. V5 is preserved
as an earlier verified package. V6 records retain their original scope and identity.

Ordinary API pre-deploy is `python -m taximobile_api.operations.railway_entrypoint migrate`.
The bootstrap deployment was replaced with a fresh normal upload: Railway
redeploy reuses a deployment snapshot, so configuration edits alone must not be
mistaken for replacing that snapshot's one-time bootstrap command. The four
one-time bootstrap inputs were [removed on 18 October](redesign/board-alpha-evidence/api-bootstrap-cleanup-20261018.json)
with per-key deployment skipped, followed by one controlled redeployment of the
existing normal-migration API build. Service settings and the other 18 variable
names remain unchanged; no values were read from Railway and no credentials were
rotated. Pre-deploy confirms head `20260908_0052`, PostGIS 3.4, 81 tables and a
restricted runtime role. All five replicas are online, with no pending work.
[Five fresh HTTP checks](redesign/board-alpha-evidence/api-bootstrap-cleanup-http-20261018-first.json)
pass, including readiness, existing synthetic-owner login, unchanged revision-1
draft and the web proxy/auth boundaries. Separate
[actual browser MFA evidence](redesign/board-alpha-evidence/api-bootstrap-cleanup-browser-20261019.json)
now passes on v7 and v8. Corrected v8 Save/Submit is recorded independently;
native acceptance remains open. Do not restore the one-time bootstrap
configuration as a recovery shortcut or expose seed values in assets/logs/docs.

On 19 October, the owner-approved
[scoped synthetic staff setup](redesign/board-alpha-evidence/scoped-demo-access-verified-20261019.json)
was applied using the existing trusted initial bootstrap/enrollment functions and
normal protected maker-checker HTTP workflow. Three synthetic MFA platform-admin
grants are non-expiring. Four Casablanca roles expire on 20 October between
11:27:04 and 11:27:06 UTC; exact grant IDs/timestamps are in the readback. No
existing account factor, city grant or cohort was replaced. Routine access changes
continue through the protected workflow. These synthetic actors do not establish
independent human staffing. A dedicated SSH key was registered under the existing
hosting authorization; it carries account/workspace access and should be removed
when terminal operations are finished. Never publish its private key or setup credentials.

The [19 October trial capture](redesign/board-alpha-evidence/railway-trial-20261019.jpg)
shows **13 days / $2.75 remaining**. All five services are online without pending
work or issues at the pre-upload check. PostGIS latest one-hour samples show
0.224 GB disk and 0.481 GB memory, close to its memory cap. No paid plan or storage
change was made. The separate [evening review](redesign/board-alpha-evidence/railway-status-20261019-evening.json)
refreshes the banner to **12 days / $2.58**, with five services online and no issues
or pending deployment work at 18:56 UTC. Recheck allowance before sustained
rehearsal and on 20 October.

At the 15 October check, PostGIS disk usage was about **0.227 GB** and memory
about **0.483 GB**, near its 0.5 GB memory cap. On 16 October the latest samples
show approximately **0.263 GB disk / 0.181 GB memory**. PostgreSQL uses 32 MB shared buffers,
2 MB work memory, 32 MB minimum/maximum WAL, 30 s checkpoints and WAL compression
to fit the trial. This is a constrained synthetic alpha, not a capacity result.
Both preserved and active volumes consume trial storage. The account showed
15 days / $4.17 remaining on 16 October. The
[17 October capture](redesign/board-alpha-evidence/railway-trial-20261017.png)
shows **15 days / $4.05**; current PostGIS samples are **0.233 GB disk / 0.234 GB
memory**. These are time-specific, not a spending guarantee. All five services
have no current issues or pending changes. The v5 hosted verification passed
98 checks on 17 October: five anonymous boundaries and all 93 packaged assets.
Fresh French password/MFA sign-in and Arabic authenticated shell rendering also
passed; complete protected-page localization and accessibility remain open. Review usage on
**18 October 2026** and before another sustained rehearsal; never upgrade billing
automatically. Trial expiry/exhaustion remains
an availability risk. Keep the original volume until the owner decides its fate.

The [17 October 09:09 UTC read-only check](redesign/board-alpha-evidence/railway-status-20261017T0909Z.json)
confirms the same five deployments online, zero issues/recent failures and no
pending work. Current PostGIS usage is 0.223 GB disk / 0.336 GB memory (one-hour
window maximum memory 0.336 GB). Billing allowance was not refreshed by this
resource check; the preceding $4.05 capture retains its own timestamp.

The [18 October read-only review](redesign/board-alpha-evidence/railway-status-20261018.json)
confirms all five deployments still successful and no staged/applying work.
PostGIS uses **0.224 GB disk / 0.290 GB memory** at the latest one-hour sample.
The [trial banner](redesign/board-alpha-evidence/railway-trial-20261018.png) now
shows **14 days / $3.26 remaining**. This completes the scheduled 18 October
allowance review; check again before sustained hosted rehearsal and on 19 October.
No billing change, new volume or deletion was performed.

The 17 October WL-2 JS production output measures **6,467,000 bytes**, versus
deployed v4's **6,245,606** (+3.54%). The reviewed fallback-JS ceiling was
**6,550,000** bytes at that checkpoint, leaving 83,000 bytes (1.28%) headroom for that required
language/entry/recovery packet. The **9,000,000-byte per-Wasm** and
**35,000,000-byte total package** ceilings are unchanged. Packaging must include
`locale.js` and load it synchronously before `compatibility.js`; missing, delayed
or reordered locale startup is rejected. This size review is not a startup
performance result. The replacement completed optimization and deployment;
[the hosted record](redesign/board-alpha-evidence/hosted-web-v5-20261017.json)
verifies its anonymous boundaries and assets. The immutable v4 package and
deployment identity remain historical rollback evidence.

The 18 October WL-3 optimized build completed in **21m59s** with **71 fresh
browser tests** passing. Its [v7 candidate](redesign/board-alpha-evidence/candidate-web-v7.json)
contains **93 assets / 29,060,729 raw bytes**, no source maps and one verified
Skiko alias. [The packaging review](redesign/board-alpha-evidence/web-v7-packaging-inputs.json)
sets the fallback-JS ceiling to **6,750,000 bytes** for the required recruitment
and applicant translations. Actual JS measures **6,635,078**, versus v6's
**6,467,155** (+2.60%); local gzip9 grows **20,655 bytes** (+1.30%). Headroom is
114,922 bytes. No framework/dependency was added; Wasm, Wasm-loader and total
ceilings remain 9,000,000 / 700,000 / 35,000,000 bytes. All eight packaging tests
pass. Compressed-file measurements do not prove hosted transfer/startup.

The compiled inputs remain frozen in their original archive. The one later
packager budget change has its own immutable input/review manifest; it does not
relabel changed application source as the compiled source. V7 was uploaded to
the existing web service as `7e30999d-719b-4f84-bda0-8bf45baccc2a`; deployment
health and all 102 exact hosted checks now pass. The scoped protected review above
records actual reads/draft retention; full protected writes and visual acceptance
are still pending.

Two 21-check REST lifecycles and two native cash lifecycles on different
candidates passed; one is on v6 and a new complete v9 trip now passes native
private acceptance through 35.00 MAD cash settlement. V8 is rejected
by actual APK configuration inspection. V9's staging/map-only values are verified
from both APKs and frozen in its manifest. This does not satisfy
the twice-run final-candidate requirement.
This establishes more than readiness, but final candidate/repeat rehearsal,
web localization, physical devices, OS push and launch gates remain open in
[board-alpha.md](board-alpha.md). Older checkpoints below are historical.

## Historical standing — 12 October 2026

### Execution checkpoint — hosted foundation verified

The owner approved Railway CLI access scoped to the current workspace and removal
of both old Palo Alto projects, including the persistent volume. Railway accepted
both deletion requests; the CLI reports scheduled deletion on **14 October 2026**.
This is scheduled removal, not a claim that its recovery window has expired.

The new [TaxiMobile Alpha project](https://railway.com/project/9f841575-c4f3-4a4d-bb83-2e6ff92e436e)
has isolated staging environment `ed891bc6-51ff-4acc-aed3-bb536931b855`:

| Service | Service ID | Verified deployment |
| --- | --- | --- |
| alpha-postgis | `41ccd6b2-41e2-4886-8d96-cc56f62aaab7` | `a3aa70b1-a40e-4e7c-afd0-482f34fb3560` — SUCCESS; `postgis/postgis:16-3.4`; private networking, no TCP proxy. |
| alpha-api | `758fa7d5-f8b8-4730-a00f-438e28184e35` | `6adc2c79-6902-477d-a046-406b30fbf46b` — SUCCESS; [HTTPS API](https://alpha-api-staging.up.railway.app). |
| alpha-worker | `eb42d0ba-feae-4f7a-9c86-48f4d38006d0` | `77a526a8-140f-4de2-9080-d6018940812a` — SUCCESS; private worker readiness requires all eight loops to succeed. |

The API and worker use the same curated 296-file backend upload snapshot,
aggregate SHA-256 `d228760fe3764322fabfa06a7bed0f343a6cba31f0c746fc444dbed3fe727560`.
Its manifest is in `.tools/alpha-delivery/backend-upload-v2-manifest.json`.
This captures the dirty candidate without committing unrelated work. The upload
contains only explicitly selected source, migrations and build inputs; no local
environment, credential store or virtual environment was uploaded.

The new [Railway entrypoint](../backend/src/taximobile_api/operations/railway_entrypoint.py)
runs `migrate` before API activation and strips migration credentials before
starting the API. Pre-deploy output proves PostGIS **3.4**, migration
`20260908_0052`, **81** public tables, a non-administrator runtime login without
public-schema CREATE, and an actual analytics projection refresh. PostgreSQL 16
requires ownership for that refresh, so only the derived
`operational_metric_facts_hourly_v1` projection is owned by the runtime role;
database/schema/base-table ownership is retained by the migration owner.
This narrow maintenance ownership is an explicit privilege, not a claim that
the runtime cannot alter its owned projection. Review separate API/worker
identities and production maintenance privileges before B/C.

An initial worker deployment failed readiness with analytics `ProgrammingError`;
the ownership correction passed pre-deploy verification and the worker's unchanged
readiness gate. `/health` and `/ready` return 200 over HTTPS. Correct Android
identity returns `SUPPORTED`; a protected ride request without authentication
returns 401, and missing client identity returns 426. Evidence is retained under
`.tools/alpha-delivery/`; these checks do not prove a hosted ride or payment.

**Resource/cost record:** all three services are capped at 0.5 GB RAM and 1 vCPU,
with one replica and a 500 MB PostGIS volume
`b9097b45-80a9-4964-9844-c247b08d1db5` in `sfo`. At inventory the trial showed
20 days / $4.85 remaining; no paid upgrade or external subscription was purchased.
Observed current memory was approximately 0.253 GB database, 0.107 GB API and
0.090 GB worker. At the documented $10/GB-month memory rate, this point-in-time
memory footprint implies roughly $4.50/month plus CPU, egress and volume charges;
it is not a bill or a sustained-load estimate. The 500 MB volume adds roughly
$0.075/month at $0.15/GB-month. Rates were checked in
[Railway's cost guidance](https://docs.railway.com/guides/claude-agent-sdk-app#control-resource-usage-and-cost)
and [storage guidance](https://docs.railway.com/guides/estimate-ai-agent-costs#the-hosting-bill).
Resource ceilings are not spending ceilings. Keep this environment intentionally
for alpha implementation/rehearsal, review usage on **13 October 2026** and before
adding routing/web, and never upgrade billing automatically. Trial exhaustion or
expiry remains a availability blocker until the owner approves further funding.

**Shutdown:** select this exact project/environment, stop/remove only the named
compute services after retaining needed evidence and synthetic state; keep the
database volume unless deletion is explicitly authorized. Confirm resulting
compute/storage billing status. Do not restore either deleted Palo Alto project
as part of TaxiMobile cleanup. No temporary public database ingress was created.

**Still incomplete:** guarded hosted synthetic cohort/reset, actual routing/place
providers, operations web, OS push and the complete two-role cash lifecycle;
physical devices, localization/visual approval and twice-run rehearsal. The
foundation is deployed; AG-07 and overall alpha remain open.

Railway is the owner's default initial deployment and hosted testing platform.
The execution checkpoint above supersedes the earlier planning-only standing.
The procedure below remains the implementation/redeployment reference; provider
and full-journey acceptance remain A-09 work in [roadmap.md](roadmap.md).

## Minimum alpha environment

Preserve the existing modular monolith and process contracts. Start with one
API instance, one worker instance from the same candidate image, one isolated
PostgreSQL service with **verified PostGIS**, and the existing operations/applicant
web artifact served on an exact HTTPS origin. Use private database networking.
Add routing/geocoding or protected shared document storage only when the shown
workflow needs it. Do not duplicate databases, add replicas or deploy the entire
production observability stack merely to obtain an alpha.

Repository references: [backend image](../backend/Dockerfile),
[configuration](../backend/src/taximobile_api/core/config.py),
[production role template](../infra/deploy/compose.production.yaml),
[deployment safeguards](../infra/deploy/README.md),
[backend setup](../backend/README.md) and [client setup](../TaxiMobile/README.md).
The Compose template describes role/security contracts; it is not a Railway
deployment manifest and must not be assumed to map directly to managed services.

| Component | Existing contract | Railway verification required |
| --- | --- | --- |
| API | `TAXIMOBILE_PROCESS_ROLE=api`; `uvicorn taximobile_api.main:app --host 0.0.0.0 --port 8000 --no-access-log --workers 1` | Verify provider ingress/port mapping and TLS; `/health` plus DB-backed `/ready`; business routes and compatibility preflight. Adapt the command to the actual assigned port if needed. |
| Worker | `TAXIMOBILE_PROCESS_ROLE=worker`; `uvicorn taximobile_api.worker:app --host 0.0.0.0 --port 8001 --no-access-log --workers 1` | Private role readiness and all eight fixed-loop heartbeats; matching and outbox processing with restart/reclaim. No public business API/worker ingress. |
| Database | PostgreSQL/PostGIS; Alembic; migration head `20260908_0052` | Extension support and version, geography queries, least-privilege runtime and separate migration authority, persistent storage and connection/pool limits. A plain PostgreSQL template is insufficient evidence. |
| Operations/applicant web | Separate browser artifact and scope-protected APIs | Exact HTTPS CORS/CSP, compatibility configuration, operations login/MFA and authorized queries; no persistent browser bearer-token shortcut. |
| Maps/places/routing/push | Existing provider adapters and device hooks | Inventory each real/simulated/unavailable mode, licenses/usage limits and credentials; verify every provider shown. OS push remains unverified until actual delivery is observed. |
| Synthetic document storage | Existing protected-document access/retention boundaries | If review/upload is shown across API/worker, use a durable shared boundary accessible to required roles and enforce authorization/deletion. Never upload real identity files for A. |

## A-08 preflight: inspect before provisioning

1. Discover the connected Railway tools and inventory projects/environments/services.
   Record target references; reuse only genuinely suitable TaxiMobile development
   resources. Never modify unrelated projects or user-owned stored data.
2. Check actual account plan/remaining credit, metering and feasible component
   sizing through available account tools/dashboard. If unavailable, record the
   missing input. Do not assume a free allowance or state an unverified price.
3. Specify the smallest justified resource limits, persistent volumes and provider
   calls; record cost estimate assumptions, monthly ceiling, review date and owner.
   Paid third-party provisioning requires explicit approval. An approved deployment
   budget should be concrete before requesting the final provisioning decision.
4. Verify PostGIS support for the selected image/service, region, backups/storage,
   private networking, runtime ingress/ports and migration execution. Railway region
   and processing arrangements are not evidence of Moroccan live-data compliance.
5. Bind an exact candidate/image and mobile/web artifacts. Inventory required
   configuration names using the existing config and environment templates. Keep
   staging isolated from production; secrets, MFA/recovery codes, credentials and
   signing material stay in protected environment/secret stores outside Git/logs.
6. Classify provider behavior: real hosted calls, clearly labeled simulation,
   unavailable with honest fallback. Synthetic data does not authorize invented
   booking/assignment/payment responses. Decide what is deliberately omitted.
7. Record who can stop spending, what is persistent versus disposable, how to
   preserve synthetic rehearsal state, and the shutdown procedure before startup.

## A-09 deploy and verify

1. Build/test the candidate with the [workflow](workflow.md) gates. Package existing
   backend/image and web roots without changing stacks. Configure required staging
   security settings explicitly; do not bypass fail-closed configuration validation.
2. Provision only the approved isolated topology. Perform migrations once with
   dedicated authority against the confirmed staging database; never run competing
   migrations from each API replica. Verify PostGIS and head after migration.
3. Start API and worker with separate role environments and bounded connections.
   Expose only TLS API/web ingress; verify readiness and worker iteration results.
   Seed through the existing reviewed synthetic tooling. A hosted reset/seed
   wrapper must add explicit target guards before use; local scripts are not
   automatically safe for remote data.
4. Configure exact Android role builds and web candidate for staging TLS, map/style
   and provider settings through existing build inputs. Check installed APK identity
   and runtime endpoint. Secrets must not be embedded in distributed clients.
5. Run real requests for auth/session/authorization including wrong actor/city;
   quote/booking; private offer/acceptance; two-device assigned ride and full cash
   lifecycle. Inspect actual authorized operations trip/payment/case records.
6. Verify REST catch-up and WebSocket delivery, outbox success/failure and restart
   recovery; perform isolated migration/connection/error drills and log review.
   Exercise map/routing/place services actually shown and app network/permission
   failures. Clearly label any simulated component in the presentation.
7. Record candidate/image/APK/web hashes, project/environment/service IDs, protected
   configuration references, endpoints, commands, UTC times, results and artifacts.
   Redact sensitive logs. A deployment badge or health-only request accepts no
   integrated workflow. Failed checks stay open in A-09; no success fabrication.

## Cost review, shutdown and rollback

Keep one staging record with purpose (persistent alpha or temporary test), service
and volume references, sized resources, actual usage/cost when accessible, budget
ceiling, next review date, accepting owner and shutdown instructions. Present the
approximate ongoing exposure with its measurement date and assumptions. Check
usage after first rehearsal and each materially changed workload; stop disposable
experiments once their evidence is collected. Keep intentional alpha resources
only when their purpose, cost and end/review date are recorded.

Before shutdown, identify exact owned targets and preserve required database/state
and artifacts. Stop public presentation access and worker/API activity using the
actual supported platform controls; preserve intentional database/volumes unless
deletion is explicitly authorized. Verify billing/resource status afterward:
stopped compute does not establish that storage billing has stopped. Remove only
authorized disposable resources. Never delete an existing user-owned service,
database or volume based on a test cleanup instruction.

For a failed candidate, stop writes as needed and return application services to
the previously verified compatible image/configuration. Do not assume reverse
Alembic migrations are safe. Schema compatibility, restore targets and rehearsal
data recovery need an explicit reviewed plan. Verify readiness and one complete
synthetic lifecycle after rollback; retain the failed candidate evidence.

## Pilot and production promotion

Milestone A staging is a technical demonstration environment. Milestones B/C
require the applicable GAP-001–019 and scoped P1 evidence in [gaps.md](gaps.md),
including legal/privacy decisions, managed backup/restore, independent security,
real provider controls, signed platforms, operational support and capacity.
Choose/approve the production region, data-processing arrangement and resource
model separately; Railway is an initial technical choice, not a legal conclusion.
Track service references and evidence in the active roadmap checkpoint. Never
mark production templates or empty evidence records accepted because A deploys.
