# Driver-document persistence decision

Prepared 24 October 2026. **Owner selected A: private encrypted S3 adapter on
Railway, source implementation only. No hosting/storage/credential apply.**
The [verified processing packet](document-storage.md) fixes scanner input/output
and storage-failure behavior. The actual separate Railway API and retention worker
still cannot share the existing filesystem adapter's volume. Both approaches below
retain the full driver-document scope; deferring documents cannot satisfy launch.

## Implementation choices

| Choice | Concrete implementation | Deployment dependencies |
| --- | --- | --- |
| **A — Private S3-compatible adapter on Railway (recommended)** | Add an adapter behind `ProtectedDriverDocumentStore`, with the existing AES-GCM payload/opaque-key associated data and API responses preserved. The API authenticates, checks application ownership/media, scans and encrypts before object upload; scoped reviewer reads proxy through API checks/decryption/audit. The separate worker erases the same objects. No public or presigned document URLs. Keep filesystem support for portable Compose and tests. Use a reviewed maintained Python SDK, bounded requests/concurrency and explicit uncertain-write reconciliation. | Dedicated private environment bucket; credential exposure limited to the existing API/worker, independent document-key custody and recoverable ciphertext/database snapshot; real scanner feeds, capacity, retention/holds and restart/outage/restore tests. Actual Trial entitlement/credit and a concrete resource/access packet precede any bucket creation or credential distribution. No paid upgrade or real documents are authorized by selecting source implementation. |
| **B — Existing filesystem adapter on an approved shared host** | Keep the documented private volume shared by separate API and worker containers, as in the current production Compose blueprint. Retain the corrected scanner, crypto, APIs and retention behavior. Prepare the host, service isolation, file ownership, shared mount and secret handling; keep Railway's alpha fallback. | An actual authorized Linux/shared-storage host and budget, private DB/routing/scanner connectivity, service lifecycle/monitoring and independent encrypted file/key backups. No host, paid service, new credential, migration or production cutover is assumed available or authorized. |

Choice A changes the storage implementation and configuration contract, not taxi
eligibility, client behavior, database authority or product scope. Choice B
preserves the adapter but changes deployment placement. Do not combine API and
worker into one process or weaken document authorization to avoid the decision.

## Provider facts and cost boundary

Railway documents private S3-compatible buckets, with no public-bucket mode.
Its current API supports object operations but does not provide server-side
encryption, versioning, object locks or lifecycle configuration. Therefore the
application's encryption and retention/hold authority remain required; native
bucket features cannot be assumed to implement them.
[Railway bucket reference](https://docs.railway.com/storage-buckets).

The published storage rate is **$0.015 per GB-month**, with whole-GB-month
rounding; services also incur egress when sending ciphertext to buckets on the
public network. API operations/bucket egress have no separate published charge.
Trial usage consumes Trial credit and can become unavailable on expiry or usage
limits. This is a published tariff, not an approved spend or evidence of this
workspace's entitlement/remaining allowance. The bucket billing page and general
Trial table differ about Limited Trial availability, so verify the actual account
rather than resolving that conflict by assumption.
[Bucket billing](https://docs.railway.com/storage-buckets/billing),
[Trial documentation](https://docs.railway.com/pricing/free-trial).

## Source implementation acceptance for choice A

1. Update the owning security/driver/deployment contracts explicitly after the
   owner's choice. Keep filesystem as the default until a complete reviewed S3
   configuration is supplied. Partial/mixed settings fail startup.
2. Preserve bounded allowed media, scan-before-persistence, authenticated encryption,
   random opaque keys, authorized/audited no-store reads and idempotent physical
   erasure. Treat uncertain upload acknowledgements and orphan recovery explicitly;
   do not blindly repeat uploads or lose the file/database consistency boundary.
3. Restrict configured endpoints to reviewed HTTPS origins, use SDK request signing
   and credential redaction, enforce timeouts/size bounds, and return actionable
   unavailable/integrity errors. Do not send plaintext files or encryption keys to
   storage or scanner logs. Do not create a competing storage framework.
4. Test clean/rejected/unavailable/uncertain results, wrong keys/tampering/opaque-key
   moves, access denial, review headers/audit, cancellation/restart, replacement,
   retention/deletion/holds and isolated ciphertext/key/database recovery. Exercise
   actual authorized S3 behavior before claiming provider acceptance.
5. Run focused/full source CI, hash-locked dependency audits and the documented
   deployment gates. Keep local, CI, provider, real participant and public evidence
   distinct. No source choice closes the actual hosting or launch gates.

This choice was requested because [AGENTS.md](../../AGENTS.md) retains owner control
over "Major architectural changes" and requires asking before making a major
architectural decision when a requirement conflicts with current documentation.
The existing filesystem contract and Railway placement are the concrete mismatch.
The [recorded owner choice](document-storage-decision-20261024.json) selects A;
[source implementation](document-s3.md) now passes all eight CI 236 jobs and
1,443 backend cases. A separately approved disposable provider probe on 25
October passes and is removed from staging; that later approval does not
authorize permanent service credentials, real documents or a paid plan.
