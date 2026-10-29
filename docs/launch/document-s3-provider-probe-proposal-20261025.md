# Disposable S3 provider probe — approval packet

Prepared 25 October 2026. **Subsequently approved and applied within the bounds
below; see the [result](document-s3-provider-probe-20261025.json).** The owner selected the private S3
source implementation; the recorded decision separately gates bucket creation
and credentials. This packet requests only the bounded synthetic provider check
below. It does not enable application ingestion or approve real documents.

## Verified scope and resource fit

The authorized CLI read confirms project `TaxiMobile Alpha`
(`9f841575-c4f3-4a4d-bb83-2e6ff92e436e`) belongs to the already authorized
workspace. Target environment is staging
`ed891bc6-51ff-4acc-aed3-bb536931b855`.

The 15:08 UTC allowance snapshot reports Trial, seven days remaining,
`remainingUsageCreditBalance=0.07505438953969135`, current usage about $0.245 and
total credit balance $0.32. These are a snapshot, not a guarantee that credit
will remain available. A later resource inventory finds zero buckets and five
services: web, PostGIS, routing, API and worker. Actual project limits report
three buckets, five services, 1 GB container memory and 500 MB volumes.
No account limit or infrastructure has been changed to obtain this evidence.

Full official-feed scanner hosting does not fit the reviewed Trial profile:
ClamAV recommends 3 GiB minimum/4 GiB preferred and describes signature-engine
memory above 1.2 GiB before scanning and transient reload memory above 2.4 GiB.
That exceeds the live 1 GB container limit. The probe runs locally with a
built-in synthetic fixture checker, not a production scanner. No additional
Railway service is proposed. [ClamAV memory guidance](https://docs.clamav.net/manual/Installing/Docker.html).

## Exact requested actions

1. Recheck this same workspace's actual Trial state and remaining usage credit.
   Require at least $0.02 available immediately before creation, no paid-plan
   change, no unrelated pending environment changes and a free bucket slot.
   Abort if any condition is unproven or the provider rejects Trial entitlement.
2. Create **one new disposable private bucket**, display name
   `tm-docs-probe-20261025`, region **`ams` (EU West)**, in the named project and
   staging environment. Capture its new bucket ID in the local operation record.
   Do not use an existing bucket or apply unrelated staged changes.
3. Retrieve only that new bucket's credentials into the local probe's process.
   Use Railway's actual `BUCKET`, HTTPS endpoint, region and addressing style;
   credentials must not be printed, committed, saved in reports, or distributed
   to API/worker/browser/mobile services. Do not retrieve or reset other secrets.
4. Execute the prepared local probe against the new empty bucket: at most **three
   built-in synthetic objects**, **32 S3 operations**, and **less than 4 KiB of
   ciphertext**. Its network work is bounded to 120 seconds, with a separate
   60-second cleanup allowance and bounded SDK close. Record cleanup authority
   locally before each write, without saving an encryption key or credentials.
5. Erase only the generated opaque keys, confirm their absence and the bucket's
   emptiness, then delete **only this newly created empty probe bucket**. If an
   outcome is uncertain or unexpected/foreign content appears, retain the
   isolated resource/ledger and report the condition rather than deleting
   someone else's data or repeating uploads. Existing services and both
   preserved PostGIS volumes are excluded throughout.

Railway publishes $0.015/GB-month with accumulated usage rounded to whole
GB-months; operations and bucket ingress/egress are free. Reserve **up to $0.02
of the existing Trial credit** for this tiny storage-only probe; no card charge,
upgrade or new paid allowance is authorized. Running from the local computer
adds no Railway application-service egress. Existing service consumption is
separate and may exhaust the available credit before approval arrives.
[Bucket billing](https://docs.railway.com/storage-buckets/billing).

The general Trial page and bucket billing page differ on Limited Trial
availability. Actual read-only limits advertise buckets for this project, but
creation/network access remains unaccepted until the provider permits it. Do
not resolve a rejection by buying a plan or widening account access.
[Trial reference](https://docs.railway.com/pricing/free-trial).

## Prepared tool and evidence

Local review tool (ignored, not part of the packaged application):
`.tools/real-world-launch/prepared_s3_provider_probe_20261025.py`.
Default invocation is `PLAN_ONLY`, without credentials or network calls.
The agent must not invoke `--apply-synthetic` until the owner approves this
resource/credential packet and the fresh preconditions pass.

The probe verifies actual private encrypted roundtrip, rejected conditional
overwrite, bounded continuation listing, ciphertext-only local recovery with
the correct/wrong keys, and a deliberately simulated lost acknowledgement after
a real write followed by same-ciphertext readback. The simulated fault is labeled
as such. Every attempted write has a durable local opaque-key ledger; result
reports omit object keys, hashes, file bytes and credentials.

Nine offline tests pass: complete bounded flow, preservation of preexisting
content, unsupported conditional writes, provider failure, failed erasure,
operation cap, fixture-only input, no-network plan mode and cancellation with
late completion/cleanup. Those tests are not actual S3 acceptance. Their JUnit
and tool hashes are bound in the companion proposal record.

No full scanner feed, app/environment/migration/TLS activation, production key
custody, real applicant file, money, participant transport, staff grant, public
launch or paid subscription is authorized. The R0–R12 goal remains intact.
