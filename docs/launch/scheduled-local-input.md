# City-local scheduling input

27 October 2026. R6/R9 implementation packet following `8514a92`, whose own
[CI 258](scheduled-review-binding-ci-terminal-20261027.json) passes all eight
required jobs. That acceptance does not cover the later source in this packet.
The full [R0-R12 goal](../real-world-launch.md) and existing domain/T0-T10 gates
remain unchanged.

## Resolution boundary

The [input requirements](scheduled-city-time.md#next-bounded-source-packet-scheduling-input)
require rejection of nonexistent local times and explicit choice for repeated
hours. The pinned shared library's default civil-to-instant conversion silently
resolves those cases. Separate native rule adapters would duplicate transition
behavior across supported platforms. Use a bounded authenticated backend read,
then retain the existing explicit-instant estimate/review/create sequence.

`POST /cities/{city_id}/scheduled-time-options` takes a date and minute clock value,
loads only a publicly visible city, and returns its current timezone, availability
flag, IANA rules version and zero/one/two distinct UTC instants with exact offsets.
It reuses the catalog's city-visibility query. A paused or unconfigured city does
not gain booking availability through this read. No quote, supply reservation,
booking, policy approval, idempotency record or business event is created.
See the [API contract](../api.md#592-passenger-immediate-and-scheduled-service).

The new `tzdata==2026.2` runtime dependency supplies the required rule files on
Windows and Alpine. Both runtime and development locks retain the reviewed wheel
and source-distribution hashes; other pins and the Linux supplement remain.
The loader uses packaged TZif files and their zone-name inventory directly, with
a bounded 128-zone cache, instead of inheriting an OS database. Missing, corrupt
or unknown configured data is an explicit sanitized unavailable error. No global
timezone search-path mutation or device-zone fallback is used. The resolver
round-trips both folds through UTC, deduplicates ordinary times and sorts actual
instants. It handles non-hour transitions and skipped days without sampling.

## Shared client boundary delivered so far

The gateway sends an authorized non-mutating POST with only date/time fields and
no idempotency key. Its typed response rejects mismatched city, timezone or clock
context, invalid/unordered/duplicate/excessive options, and offsets or local
labels that the client cannot faithfully render. Unknown capability (`404` or
`405`) and rule failure (`503`) are explicit errors, not empty gap responses.
Cancellation, transport loss and rejected authentication retain their existing
distinct behavior, with no automatic gateway retry.

The coordinator publishes only the latest matching read under the existing
credential-owner fence. Session recovery may retry this declared read once;
logout/replacement cannot publish the previous owner's options. No booking
command is invoked. A gateway without the capability returns an explicit null
that becomes localized unavailable copy rather than invented options.

## Remaining input integration

The passenger screen still uses manual RFC3339 input at this checkpoint. This
packet delivers the backend and shared read boundary; it does not claim a
completed passenger picker. Continue with the following directly dependent work:

1. Wire compact date/calendar and 24-hour time controls with visible city context
   through the existing Android/iOS action gate. Keep typed correction available.
2. Tag each user-requested clock read with a fresh presentation identity. Match
   that identity plus current city/timezone/date/time and trip context before
   adopting options. Retained matching data after a failed read must not be
   mistaken for a fresh successful response. Clear selection/review on edits and
   navigation-owner changes; reject delayed replies.
3. Keep zero-option gaps unconfirmable with an adjustment message. Select a unique
   option, or require an explicit visible offset choice for an overlap. Only
   then obtain the existing backend fare/terms review. A clock read never submits
   creation; confirmation still passes the independent estimate/request fence.
4. Preserve validated selection through ordinary price readback while keeping
   it session-owned and tied to the current form. Handle missing capability,
   retry, metadata/rule changes, composition/process recreation and cancellation.
   Do not use cached clock options as pricing or booking authority.
5. Verify point/fixed-route flows, all languages/styles/RTL, 200% text and actual
   picker/keyboard behavior. New UI/native wiring and exposed states require
   their own tests and immutable platform/package evidence.

## Evidence and limits

The [source checkpoint](scheduled-local-input-verification-20261027.json) binds
the implemented boundary to backend unit/API/PostGIS and shared/gateway/Android
checks: 1,212 backend unit cases, one real HTTP/PostGIS case, 224 affected JVM
cases, 387 Android-host cases, both debug role builds and 121 source/build-tool
cases pass. The catalogs validate 1,296 entries each; both hash-locked dependency
audits pass. Test sets overlap. The first focused backend run retained two failures:
Python's clock parser normalized `24:00`, and a synthetic active-city fixture
lacked its configuration field. Strict ASCII hour/minute bounds now reject
`24:00` explicitly; the corrected fixture covers configured, unconfigured and
paused states. Failures remain retained.

The real HTTP case uses a fresh local PostGIS cluster migrated to 0054. Actual
token/session authentication and SQL visibility apply; all six booking, offer,
commitment, event, idempotency and outbox counts remain unchanged. The separate
owned test cluster is stopped after verification, with its data retained. The
preserved database cluster and hosted resources are untouched.

Fresh CI must verify this successor's full backend suite, native products,
dependency/image audits and production web caps/boot. Local source evidence and
the predecessor's CI cannot establish those results. Physical Android remains
deferred; signing/store, iOS devices, low-end latency, linguistic/assistive,
hosted/provider, operational, pilot and public acceptance remain separate.
Preserve the Trial-only hosting stop, both volumes, rollback archives and
unapplied TLS/migration packet. Never replay credential/MFA recovery or the
completed bounded S3 probe.
