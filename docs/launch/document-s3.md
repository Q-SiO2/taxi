# Private S3 document implementation

Owner selected this source work on 24 October 2026 in the
[persistence decision](document-storage-decision-20261024.json).
Status: **source workflow implemented; qualified local checks pass; native CI and deployment acceptance pending**.

Retain `ProtectedDriverDocumentStore`, the `TMDOC1` AES-256-GCM envelope,
opaque-key associated data, bounded media/scanning, scoped/audited API reads and
retention erasure. Filesystem remains the portable default. S3 adds a private
shared persistence adapter for the separate Railway API/worker; no public or
presigned document URLs or client-side storage credentials.

The backend SDK is pinned `boto3==1.43.118`, verified against current PyPI and
official SDK documentation. This is a necessary S3 transport dependency to use
maintained request signing/response handling rather than inventing a signing
implementation or another service/framework. Existing package pins must remain
unchanged unless a concrete resolver/audit finding requires a documented repair.
Runtime/dev/Linux hash locks and native CI retain their current validation gates.

Configuration must be complete and immutable: explicit provider, reviewed HTTPS
endpoint/bucket/region/addressing style, explicit bucket credentials (redacted from
repr/errors), independent encryption key and scanner configuration. Mixed S3/file
settings and partial configuration fail startup. SDK verification remains enabled;
ambient credentials/instance metadata must not become an implicit credential source.

One conditional upload uses a random opaque key and ciphertext only. Disable
automatic write retries. An uncertain acknowledgement requires bounded readback
and exact encrypted-payload verification, not another upload. Reads must be
size-bounded and authenticated; missing objects and unavailable/integrity failures
remain distinct. Delete is idempotent, but cannot silently accept provider errors.
Constrain concurrency, connection/read deadlines and response-body lifetime.

File/object/database commit gaps, interruption, pending cleanup and process death
require durable reconciliation before this capability is exposed to real documents.
Do not present a readback alone as proving orphan recovery. Reuse existing model
and retention machinery where correct; any schema/transaction change must be
deliberate, documented and tested. Keep safe accepted behavior during migration.

Implementation/acceptance sequence:

1. Configuration, shared envelope and bounded S3 adapter with meaningful unit/SDK
   protocol tests, credential/endpoint/error redaction and cross-adapter recovery.
2. Durable upload/outcome and orphan-recovery handling across API/database/worker,
   with cancellation, concurrent/deadline and process-restart evidence.
3. Actual authorized S3 behavior, scanner feed, snapshot/key recovery, retention,
   reviewer and scoped client journeys, followed by exact-source CI and controlled
   hosting deployment verification.

All three remain required. This packet does not authorize bucket creation,
credential distribution, paid resources or real participant documents. Existing
Trial-only spending, preserved volumes, source CI and full R0–R12 gates persist.

## Transport progress and next consistency packet

The SDK/hash-lock installation adds six packages and preserves every previous
runtime/development pin; the Linux supplemental lock is unchanged. Both local
dependency audits report no known vulnerabilities. Configuration and transport
tests use SDK model/HTTP-response probes and synthetic objects, not a real bucket.
The historical [transport verification record](document-s3-transport-verification-20261024.json)
binds 87 focused and 1,115 full unit passes with no failures/errors/skips, clean
runtime/dev audits, retained failures and source hashes. The adapter and
configuration were not wired into API/worker activation at that checkpoint.

An observed SDK trap is retained: standard one-attempt configuration still
replayed a PUT for region redirect/signing errors. A first retry-event guard now
rejects error responses before retry/region discovery. Real SDK response tests
verify exactly one PUT and one explicit GET readback for 503, 301 and malformed
region errors, with no second PUT or bucket discovery. The earlier two failed
assertions and the initial SDK config-observer failure remain evidence.

The durable implementation uses a database record **before**
filesystem/object publication; a Python future or exception payload is insufficient.
The minimal model change reuses document metadata for hidden uncommitted
uploads, with an explicit lease and an uncommitted-upload erasure reason. No
evidence link or application version advances before confirmed publication and
the final authoritative expected-version transaction. Finalization clears the
pending state; failures, cancellation and process death leave recoverable metadata.
Any migration must be deliberate and documented as new source evidence, never
inherited from the previously tested 0053 restore.

The retention process must skip active upload leases, recover expired pending
uploads and retain content-free erasure evidence. It must also reconcile old,
unreferenced objects so a late provider completion cannot escape a one-time
cleanup. Object listing and work per iteration must be bounded and paginated;
only the strict owned opaque namespace is eligible. Missing database authority
fails closed. Key-scoped database locking must serialize creation of an upload
record with an orphan check/delete: a check followed by an unprotected DELETE can
otherwise race a newly referenced object. Test that interleaving explicitly.

Keep existing document deletion/retention, scoped reads, schema compatibility and
file/database unknown-result recovery as acceptance requirements. Expose no new
S3 settings through the application factory until that workflow and its tests
exist. Official feeds, real S3 semantics, physical clients, capacity and retention/
privacy acceptance remain subsequent independent gates.

## Durable workflow — 25 October 2026

`prepare` validates, scans and seals bytes without storage publication. The API
then commits a hidden document row and a five-minute upload lease under the
application/version and opaque-key locks. Only then does `publish` write the
prepared ciphertext. A final transaction refreshes the locked application,
requires the same expected version and an unexpired pending document, clears its
lease/deletion marker, links evidence and advances the version once. Pending
rows never appear in applicant/reviewer document lists or complete a requirement.

Cancellation, process death, provider uncertainty and rejected/stale finalization
leave durable cleanup authority. There is no request cleanup after an uncertain
activation commit: that commit may actually have succeeded. The worker skips
active leases, erases expired pending uploads and writes the immutable
`UPLOAD_UNCOMMITTED` action. Migration `20261025_0054` and its guarded downgrade
are defined in [database.md](../database.md). Schema rollback refuses to discard
pending recovery or immutable new-reason history; plan a compatible forward fix
or a separately accepted protected rollback before hosting activation.

Repeated bounded orphan sweeps catch late writes after a pending row has already
been erased. Each page uses at most the configured batch size (1–1,000 entries),
S3 continuation tokens or an owned filesystem iterator. Foreign entries consume
filesystem work slots; only strict owned opaque names are eligible. Five-minute
object age protects recent writes. The worker takes the same key advisory lock
as upload registration and rechecks the database before deletion. Missing
database authority fails closed. Restarts can rescan safely; page bounds do not
establish an overall fleet cleanup deadline or production capacity.

Filesystem staging now uses a deterministic `.upload` sibling of the durable
key, so termination before rename is recoverable. Both final and staging bytes
are erased together; old untraceable `.upload-*` files require a separate rollout
inventory/disposition rather than deleting foreign names. Filesystem reads now
bound ciphertext size before decryption. Iterator handles close on shutdown.
S3 keeps its conditional single PUT, exact-ciphertext acknowledgement readback,
SDK retry guard, bounded response reads and in-flight slot ownership.

Known-document erasure retains the existing immutable database evidence.
Genuine orphans have no known applicant/city/actor; they emit only the fixed
operational message `Protected document orphan erased.` and worker label, with
no content, key, hash or invented audit principal. Central log delivery and
retention still require hosted acceptance; this is not individual durable
database evidence for an unreferenced object.

The source factory, API and worker now share the explicit backend selector:
`TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_BACKEND=filesystem|s3` (default filesystem).
S3 requires its explicit endpoint, bucket and credentials plus the independent
encryption key and ClamAV host; file/S3 settings cannot be mixed. Partial or
implicit configuration fails startup, and document encryption/credentials are
redacted from configuration repr/errors. Owned SDK clients and listing handles
close during process shutdown; an inline worker does not close the API's shared
store. No hosted environment values, bucket or credentials have been changed.

Seventeen isolated PostGIS recovery/HTTP cases pass, including actual writer
termination before/after rename, cancellation with late completion, both key-lock
orders, competing finalizers, cached-version refresh, migration roundtrip/refusal,
and normal/lost-commit-ack lifecycles across memory, encrypted filesystem and a
controlled S3 client. Source inputs did not change during that run. The local
runtime is PostgreSQL 16.14/PostGIS 3.5, not the hosted/CI 3.4 target.

Subsequent review found a real lease bug: a lock wait could outlive the timestamp
captured before waiting. The retained regression fails before the correction.
The final activation now checks the clock after all document/evidence/replacement
locks; three actual SQL-wait regressions pass without mutation after expiry.
The [database records](document-upload-recovery-r5-20261025.json) bind this later
source separately; the earlier 17 passes are not transferred as exact-source CI.

All 1,142 unit cases pass in the broader local report. Its first API pass had
one failure because a two-second socket JWT expired during test-app startup;
minting after startup retains the original two-second expiry/three-second close
assertion, and all 62 API cases now pass. Retain the initial tri-language fixture
failures, non-propagating-logger observer failure, lock regression and timing
failure. They are not green runs. The original 0053 database is preserved, the
0054 template is isolated, and the owned cluster is stopped after every run.
Native full-suite CI, actual provider/physical/release acceptance remain required.

The [workflow verification record](document-storage-workflow-verification-20261025.json)
binds these reports, retained failures, source hashes, clean 48-package runtime/
74-package development audits, compilation/documentation/credential/CI-security
checks and preservation of the original root index and all 371 mobile/web
compilation inputs. No dependencies beyond the six SDK transport packages were
added, and all earlier pins plus the Linux supplemental lock remain unchanged.

A final [listing ownership correction](document-listing-cancellation-verification-20261025.json)
reproduces shutdown closing an executing filesystem generator after repeated
caller cancellation. The listing job now owns lock release until its thread
finishes; abandoned exceptions are observed without emitting private paths.
The pre-fix regression is retained and all 185 affected/configuration/worker
checks pass after correction. Its two changed source inputs are bound separately
from the prior checkpoint; native full-suite CI still owns final acceptance.
