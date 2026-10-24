# Protected driver documents — scanner and recovery

Prepared 24 October 2026 for R3/R8. Status: **local correction verified;
fresh source CI and actual deployment acceptance pending**.

The [actual hosted preflight](staging-document-storage-preflight-20261024.json)
finds root/key/scanner settings absent and zero files: driver-document ingestion
is disabled. A database-only backup does not contain document files or their
decryption key. No real participant document, hosting resource, grant, credential
or provider configuration has been changed by this packet.

## Corrected processing boundary

The original scanner accepted any response ending in `OK` after a single TCP
read. Regression probes reproduce **11 failures / 7 passes**: truncated or
malformed success and incomplete connection responses could pass, and an ordinary
fragmented valid response could fail. The failed observation is retained.

The adapter now streams bounded chunks with backpressure, consumes no more than
4,096 reply bytes through daemon connection closure, and requires exactly one
`stream: OK` NUL-terminated record. Fragmented records work; malformed, multiple,
trailing, oversized and scanner-error records fail unavailable. A well-formed
malware record rejects without echoing its signature. One deadline covers the
whole exchange and cleanup is bounded. External cancellation still propagates.
These rules follow the vendor's [INSTREAM/non-session protocol](https://docs.clamav.net/manual/Usage/ClamdProtocol.html).

No encryption/schema/API convention or dependency changes. AES-256-GCM, random
opaque names and storage-key associated data remain. Atomic publish failures
map to the existing document-unavailable/503 boundary, without exposing a private
path in HTTP detail; temporary ciphertext is removed. Failed or incomplete scans
never persist a document.

## Evidence and limits

The [source verification record](document-storage-verification-20261024.json)
binds regression logs, final test reports and source hashes. Thirty-two focused
cases cover the real loopback TCP exchange and encrypted store. They use a
protocol fixture and synthetic file bytes; they do not establish a production
antimalware daemon or current vendor signature feeds.

All **1,060 unit tests** pass without failures/errors/skips. Two
[HTTP/PostGIS lifecycle cases](document-lifecycle-local-20261024.json) pass using
both memory and the actual encrypted-filesystem adapter: owned upload, protected
review, replacement and physical retention erasure. A filesystem publish failure
returns 503 without changing application version or metadata and leaves no file.
The existing synthetic test cluster is stopped and retained; its PostGIS 3.5
runtime differs from Railway/CI 3.4. Native CI must verify the supported target.

The [real local ClamAV 1.5.4 probe](document-scanner-daemon-20261024.json) passes
five checks: clean/encrypted roundtrip, rejection of a harmless custom hash
fixture without a new file, stopped-daemon unavailability, daemon restart plus
ciphertext-copy recovery, and physical erasure. Both owned foreground daemons
are stopped and the loopback port released. No Windows service, antivirus
exclusion, real malware, participant document or persistent application key is
created. This is actual daemon protocol acceptance using one custom signature,
not official signature-feed coverage/freshness or hosted scanner acceptance.

The portable package's [detached vendor signature is verified](document-scanner-runtime-r4-20261024.json)
using the vendor's published public key in an isolated local GPG keyring. Keep
the [first key-download HTTP failure](document-scanner-runtime-20261024.json),
[inline-page HTTP failure](document-scanner-runtime-r2-20261024.json) and
[MSYS path/import failure](document-scanner-runtime-r3-20261024.json). The final
continuation uses the public key as returned from the official download page by
the web tool and corrects GPG path handling. The original ZIP/signature is reused;
no archive redownload or verification bypass occurs.

Synthetic ciphertext-only copies recover using a newly constructed adapter and
the separately supplied correct key for PDF/JPEG/PNG-signature fixtures. A wrong
key fails; restoring the right key succeeds without changing ciphertext. Moving
ciphertext under another valid opaque name fails associated-data authentication.
These are adapter recovery checks, not real-document, metadata/snapshot,
retention/holds, independent custody, production backup or RPO/RTO acceptance.
Cancellation during the scan is covered; interruption during atomic filesystem
publication, file/database commit gaps and process death still require separate
consistency/orphan-recovery evidence before real-document acceptance.

## Hosting decision still required

The existing filesystem adapter requires API and retention worker access to the
same private persistent files and key. The portable Compose deployment supplies
that shared volume. Railway's [current volume contract](https://docs.railway.com/infrastructure-as-code/reference#volumes)
attaches a volume to one service; equal paths or equal environment variables in
separate services do not establish a shared filesystem. Mounting a volume only
on the API cannot establish retention-worker deletion.

Keep ingestion disabled until a reviewed target topology satisfies that existing
contract, or an explicit owner-approved architectural change supplies equivalent
private persistence, erasure and recovery. Do not silently introduce public
object URLs, duplicate independent stores, a new storage service/framework or a
combined API/worker process to conceal the mismatch. Both preserved PostGIS
volumes and Trial-only/no-purchase constraints remain binding.

The next deployment packet must bind: actual private scanner/healthy current
signatures and capacity; persistent cross-process storage permissions; independent
key custody/recovery; consistent database/ciphertext snapshot and bounded restore;
owned upload, scoped/recent-MFA review, replacement, retention and deletion;
clean/rejected/unavailable cases; and actual restart/rollback evidence. Real
documents require the existing participant/privacy/retention approvals. None of
those gates is closed by this source correction.
