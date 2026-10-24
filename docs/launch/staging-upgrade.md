# Staging upgrade preparation — 24 October 2026

Status: **source CI, encrypted backup and qualified local restore/migration pass;
hosted upgrade not applied**.
R3 follows the [source/dependency correction](dependency-refresh.md). This is the
existing authorized synthetic alpha, not a newly accepted Fès production service.
The [R1 decisions](r1-decisions.md), Trial-only ceiling and preserved volumes remain
binding. Never replay the previous credential/MFA recovery.

## Live database baseline

The [read-only database record](staging-database-preflight-20261023.json) comes
from the existing API deployment and a single `READ ONLY` transaction using its
runtime connection. It verifies:

- PostgreSQL **16.4**, PostGIS **3.4**, Alembic **20260908_0052**, 81 public base
  tables and about **41.8 MB** database size. The separately observed active
  500 MB volume uses about 219 MB; database size is not volume consumption.
- The 81 table owners are `taximobile_owner`. `taximobile_runtime` has no
  superuser, CREATEDB, CREATEROLE, replication, RLS-bypass, public-schema CREATE
  or inherited group membership authority.
- `operators.requires_active_membership` is absent. The source's union admission
  policy is **not yet deployed**; source and local tests do not establish hosted
  enforcement.
- The actual API-to-PostgreSQL connection is **not using TLS**. Private networking
  alone does not satisfy the production TLS requirement in
  [database.md](../database.md#45-backup-and-recovery). This must be resolved and
  tested with certificate/hostname verification before production acceptance.

No role/grant, DDL/DML, materialized-view refresh, data/seed, secret, deployment,
service/volume or spending mutation was performed. Local portable PostgreSQL is
16.14 on the same major line; its exact PostGIS extension compatibility must be
checked before restore rather than inferred from the PostgreSQL version.

## Next bounded sequence

1. Observe exact source **90704d136ca32ad7212243208fac92c606e1764d** CI to terminal
   acceptance. Retain the predecessor's audit failure; do not borrow another
   source's green jobs or loosen the hash/vulnerability gates.
2. Create an encrypted off-host backup of the confirmed existing alpha using
   existing operator authority, never the ordinary application role. Keep all
   data/credentials outside Git and logs. Record target, encryption/key custody,
   archive hash, source versions and capture consistency. Refuse to overwrite a
   previous archive. A protected local rollback copy is not continuous production
   PITR, independent recovery ownership or approved retention/RPO/RTO evidence.
3. Restore once into a newly named isolated local verification database on the
   compatible PostgreSQL/PostGIS line. Do not overwrite the rehearsal/test/live
   databases or use a live provider connection from the restored service. Compare
   schema objects and aggregate row counts; verify the existing baseline before
   running migration 0053 and its membership/default/backward-compatibility checks.
   Preserve the original encrypted archive and record target disposition.
4. Prepare matched API/worker artifacts and deliberate migration authority from
   the accepted source; inspect the existing pre-deploy/grant protocol. Verify
   restricted runtime reads/writes after the new column and preserve accepted-trip
   completion, ordinary passenger access and existing open-participation defaults.
   Do not silently enable member-only policy against an unverified real roster.
5. Prepare TLS and full certificate-verification configuration for database server,
   API/worker/migration/backup consumers, with protected key custody and a rehearsed
   rollback. Test correct CA/hostname, rejected wrong trust/hostname and actual
   encrypted sessions. No certificate or privilege shortcut substitutes for this.
6. Apply only the reviewed staging upgrade within the existing authorization and
   Trial capacity, then verify exact images/schema, health/readiness, worker/event
   operation, both web/native compatibility and scoped synthetic membership/session
   workflows. Preserve both volumes and the alpha rollback path. Production
   funding, provider/field/device/operations acceptance and public activation remain
   separate gates in the full [launch plan](../real-world-launch.md).

## Evidence obtained on 24 October

All [eight required CI jobs](dependency-refresh-ci-terminal-20261024.json) pass for
the exact source above, including backend, Android/web, unsigned iOS simulator,
documentation/provenance, wrapper, resolved graph and complete dependency review.
Backend image publication is skipped for the draft PR. This does not sign a
release, close device/field gates or establish an accepted hosted image.

The [backup record](staging-backup-20261024.json) binds a **617,690-byte** custom
archive to an exact exported repeatable-read snapshot and counts for all **81
public tables**. Capture uses the existing owner over a local database socket and
encrypted SSH transport. The archive is stored off-host under operator/SYSTEM
directory permissions and Windows CurrentUser DPAPI; its decryption/hash and
archive table-of-contents checks pass. No plaintext dump file, role-password dump,
source data/schema change or source credential/MFA operation occurred.

This is a database backup, not a document/object-store or global-role backup.
Current-user key custody is not independent recovery ownership; one local copy is
not approved production PITR, retention, RPO/RTO or backup-expiry evidence.

The [terminal restore continuation](staging-restore-r2-20261024.json) reuses that
original archive in an ACL-restricted, authenticated loopback-only cluster. Full
archive import passes, all 81 public-table counts match the captured snapshot,
and migration **0052 → 0053** preserves those counts and public relation counts
while adding the expected constraint. Runtime DDL is rejected; enabling membership
without a linked register is rejected in a rolled-back probe. The restored
operator's policy stays false. Actual test-environment application health and
readiness return **200** using the restricted runtime. No external worker/provider
was started. The cluster is stopped and retained, with the encrypted archive intact.

The [restore runtime](restore-runtime-20261024.json) is PostgreSQL 16.14/PostGIS
3.4.2 on Windows, compared with source 16.4/3.4.3 on Linux. Same-major/minor-line
logical compatibility was exercised; exact patch, platform and collation parity
were not. Non-public extension tables were imported, but their totals were not
independently compared with the source snapshot. The final continuation's 10.554
seconds excludes earlier setup/failures and is **not an RTO measurement**.

Preserved failures matter: [the first controller observation](restore-controller-observation-20261024.json)
records an inherited startup-pipe wait while PostgreSQL was already running. The
controller was repaired without restarting that live cluster. The
[first restore](staging-restore-20261024.json) then failed atomically when the
ordinary owner could not create additional PostGIS extensions. The successor
verified no application tables survived, used the existing local administrator
for trusted import, then assigned application-table ownership separately and
rechecked the non-superuser runtime. No live privilege was expanded and no new
backup was captured to hide a failure.

The [document-storage preflight](staging-document-storage-preflight-20261024.json)
finds all three storage/encryption/scanner settings absent and zero files in the
expected private directory. This is **disabled hosted document ingestion**, not
functional driver-document acceptance. Persistence, scanner operation and protected
file backup/restore remain R3/R8 work before real participant documents. The
database-only backup must not be presented as proving those capabilities.

CLI usage/status reads preserve the existing Trial-only authorization. Usage
totals alone do not identify the plan or remaining credit; no budget, subscription,
resource, volume or service change was made. Verify current funding before an
operation that can incur new hosting charges. TLS and matched API/worker rollout
checks remain the next hosted technical work; hosted schema is still 0052.
The [database TLS packet](database-tls.md) now implements one verified transport
policy and passes local trust/rejection probes with an observed restricted
TLS 1.3 session. New exact-source CI must execute its disposable Docker fixture;
this does not change the non-TLS hosted baseline described above.

## Membership-aware rollback boundary

The preserved pre-policy alpha is a staging fallback only while every operator's
membership requirement remains false. Once a union operator enables the policy,
do not serve new work using older API/worker code that ignores it, or drop the
column as a rollback shortcut. Retain a policy-capable rollback version; any older
fallback needs a separately verified pause of new admissions/dispatch that still
allows accepted trips and financial completion. A green old build cannot authorize
non-member work or silently relax the owner's closed-shop rule.
