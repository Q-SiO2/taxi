# Staging recovery and final presentation pair — 23 October 2026

## Current acceptance checkpoint

Recovery is applied; do not replay the credential/configuration cutover.
[Final integrated verification](board-alpha-evidence/release-v23-r2-integrated-verification.json)
passes native v23 / live web v10 / the recovered API pair twice. Both 35 MAD
cash rides complete with eight successful business requests exactly once, the
same passenger process, quote resume and observed driver radio recovery.
Driver ends offline and pending cash zero. Seven-beat times are **16:22 / 11:07**;
first-run observer/continuation/session-expiry and metadata bookkeeping
qualifications remain explicit. There is no uninterrupted-video or timing promise.

Web v10 deployment `da158b10-2d82-468e-b1f1-cffba5c32ee4` is live. Its
[103 hosted checks](board-alpha-evidence/hosted-web-v10-20261023.json) pass all 93
asset hashes, relative HTTPS applicant redirect, headers and API boundaries.
[Actual selected visual review](board-alpha-evidence/web-v10-hosted-visual-review-20261023.json)
passes four Arabic timeline styles, live Notepad continuity and French/English
Notepad. Capture recovered when the owner kept the browser panel open. Empty/stale
AX after preferences did not establish a blank rendered app; screenshot-based
review resolves the visual question, while full accessibility remains open.

[Normal staff MFA/read/logout](board-alpha-evidence/web-v10-staff-session-review-20261023.json)
uses the same authenticator and baseline Casablanca scope. Matching applicant
reads and normal logout pass. No expired role, seed or recovery code was replaced.
[Fresh final provider identities](board-alpha-evidence/release-v23-r2-final-deployment-identities-20261023.json)
confirm all five exact paired heads are successful, one active each.

The next step is owner review using [the handoff](../board-alpha-handoff.md) and
[presenter script](../board-demo.md), then bounded corrections or later pilot
acceptance. Physical Android remains deferred; iOS, field transport, real money,
full accessibility, all 213 views/states and public launch are not accepted.

## Recovery evidence and historical preparation

Railway's [22:49 UTC update](https://status.railway.com/) reopens Free and Trial
deployments. The approved CLI account works; the connector still requires
reauthentication. Continue with the existing authorized CLI and five staging
services. Keep the Trial plan and both volumes. No new authorization is needed
for the already authorized isolated staging work.

Native v23's first [seven-beat functional run](board-alpha-evidence/v23-board-first.json)
passes in **8:59**, paired with hosted web v8/API v6. Its independent
[provider trace](board-alpha-evidence/v23-native-first-http.json) confirms eight
successful business requests once each. Those results retain their exact
deployment and artifact identity. The later process/session gap ended the
emulators and temporary browser tabs; no normal browser logout is inferred.
The two final repetitions linked above use the stable resulting deployment pair.

Actual hosted v8 Arabic timeline markers appear as missing-glyph boxes. The
[exact prepared web v9 reproduction](board-alpha-evidence/web-v9-ar-timeline-glyph-rejection-20261022.json)
confirms the defect. Web v10 changes only `ApplicantApplicationEditor.kt`:
theme-colored vector circles replace decorative text glyphs, with centered
alignment and the existing current status exposed through row semantics.
Labels, order, application identity/version, authority and commands remain
unchanged. Native APK/shared sources remain v23; this web-only file is not
compiled into Android. Fresh JS/Wasm checks, optimized freeze and hosted HTTP
verification now pass. Selected hosted language/style observations now pass as linked above; broader visual acceptance remains scoped.

The provider recommends rotating environment secrets and reviewing service logs.
[Live read-only preflight](board-alpha-evidence/railway-live-credential-preflight-20261022.json)
confirms migration `20260908_0052`, 81 public tables, restricted runtime access,
no unexpected login roles, four valid encrypted MFA records and 40 recovery-code
rows. The database has no public TCP proxy. Both existing owner and runtime
passwords connect. Existing API pre-deploy uses the normal migration adapter,
not synthetic bootstrap.

[Matching replacements](board-alpha-evidence/railway-credential-recovery-prepared-20261022.json)
and [four MFA ciphertext replacements](board-alpha-evidence/railway-mfa-rekey-prepared-20261022.json)
retain the **prepared** checkpoint. [The applied recovery journal](board-alpha-evidence/railway-credential-recovery-application-20261022.json)
now records ten matching configured bindings, two existing role-password changes
and four MFA ciphertext replacements committed atomically, followed by actual
service recovery. Windows current-user DPAPI protects the private
old/new bindings and encrypted rollback records in ignored workspace storage.
No plaintext seed, credential value, connection URL or secret-derived hash is
included in documentation/evidence. The existing authenticator seeds, credential
identities, replay counters, recovery codes and grants must remain intact.

**Actual recovery outcome:** new owner/runtime passwords connect; both old
passwords are rejected; no pre-cutover client connection remains. All four MFA
records decrypt using the new key and reject the old key. Migration
`20260908_0052`, 81 public tables, restricted runtime privileges and all 40
recovery-code rows are unchanged. [Runtime boundary checks](board-alpha-evidence/railway-recovered-runtime-boundaries-20261022.json)
pass API/worker health and DB-backed readiness, new monitoring authorization,
unauthenticated/old-token rejection, and normal synthetic driver login/read/logout.
The new driver JWT is privately verified against the new signing secret and
rejected against the old secret. Driver is offline; pending cash is zero.

The DB replacement retains its exact image and active volume. The initial API
reuse attempt could not deploy: provider metadata explicitly reports
`canRedeploy=false`. One new upload uses all **298 exact frozen API v6 files**,
not current backend worktree changes. The supported worker redeploy also creates
a new image. [API](board-alpha-evidence/railway-recovered-api-source-20261022.json)
and [worker](board-alpha-evidence/railway-recovered-worker-source-20261022.json)
authored runtime/config/lock bytes match frozen v6 and v5 respectively; six
generated setuptools metadata files are identified separately. Both new image
digests and the failed image-equality observer are retained. Do not describe
these two rebuilt images as byte-identical to their predecessors. Each recovered
service has one successful active deployment. Normal staff MFA/read/logout and
corrected web rollout now pass; the final-pair synthetic path passes with the qualifications above.

The [provider PostgreSQL guide](https://blog.railway.com/p/security-disclosure-recommendation-rotate-postgresql-database-credentials)
requires password/config synchronization, consumer redeployment and verification
that old credentials/connections no longer work. Its database-view Regenerate
flow targets the Railway template. This custom PostGIS deployment has separate
owner/runtime roles and no public CLI Regenerate operation; use the prepared
guarded DB/config sequence, preserving the existing role boundaries and volume.
Do not change only `POSTGRES_PASSWORD` or leave consumers with mismatched values.

Historical intended sequence (actual outcomes above supersede it; do not replay):

1. Confirm source/image/deployment identities, volume attachment/headroom and
   matching current bindings; review scoped logs and preserve any anomaly.
2. Set the matching DB/API/worker variables with deployment triggers skipped;
   verify every configured binding privately. No unrelated variable changes.
3. Under the existing deployment advisory lock, update both existing role
   passwords and four MFA ciphertexts in one owner transaction. Verify the same
   seeds inside the private process and preserve counters, recovery rows and
   schema. Retain the protected rollback material.
4. Redeploy the same PostGIS image on the same active volume to drop old
   connections; then redeploy the exact existing API/worker images with their
   matching new bindings. Do not reseed, add grants or alter pricing/commands.
5. Verify new/old credential acceptance/rejection, image identities, readiness,
   restricted runtime, schema/table count, MFA decryption and monitoring guards.
   No full forensic clearance or unconfigured external-monitor assurance is
   inferred from these scoped checks.
6. Deploy the exact corrected web package; verify hashes, HTTPS `/apply`
   redirect, security headers, proxy, normal staff MFA and applicant reads.
7. Establish normal synthetic sessions and complete two final-pair emulator
   presentation repetitions. Retain all prior failures/qualifications. Physical
   Android remains deferred; field, real-money, pilot and public gates stay open.
