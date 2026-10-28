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

## Native input integration in the next source candidate

The working source after published `d95de9e` replaces manual RFC3339 entry with
date/calendar and 24-hour time controls. Typed Arabic and Eastern Arabic digits
normalize before the strict ASCII wire request. The point flow shows the sole
available city by name or requires an explicit city choice among multiple cities;
it no longer uses catalog order at review/create. Fixed-route scheduling uses its
published direction's catalog city. The existing Android and iOS action gate
starts both time and fare reads.

Each clock request carries a new presentation-only read identity, and each price
review carries a separate one. A result is adopted only for the current city,
zone, date, time, form and session owner. Editing or changing city, route or
points drops the selected instant and old review. A successful single option
selects its exact UTC instant; a gap shows correction copy; a repeated hour
requires an explicit visible offset choice. The time-check button remains
available after selection so changed rules can be checked again. Starting that
read clears previous clock and price authority even if the response fails.
Only a selected instant can start the existing backend price/terms review, and
confirmation still has an independent estimate/request match.

The saveable form retains date and time text only. It does not save the clock
result, read identities, chosen instant or price authority across recreation.
The new JVM UI tests cover Fès after another first city, fixed catalog city,
gap, explicit overlap selection and changed review, failed recheck, calendar/time
controls, plus all twelve language/style combinations at 200% text. Draft tests
cover digit normalization, stale reads, city metadata and restoration. These are
source checks; candidate-linked Android/iOS, browser package, physical device,
provider and operational acceptance are still required. The local JS and Wasm
browser suites passed 86 cases each, the production package passed unchanged
size caps, and four Chrome compatibility/boot scenarios passed with zero T4
catalog-case or deployment acceptance. The refreshed Android host suite passed
394 cases, and both passenger and driver debug APKs built. These local outputs
are not signed distribution or physical-device evidence.

The [native source-hash checkpoint](scheduled-local-input-verification-native-20261028.json)
records the 19 changed source files, six affected JVM classes (134 cases), 394
Android-host cases, 86 JS and 86 Wasm browser cases, both debug role builds,
the unchanged web-package caps and twelve large-text language/style captures.
Test sets overlap and must not be summed. It is local source evidence until the
exact candidate passes its own immutable CI run.

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

The published `d95de9e` source boundary now has [terminal CI 260 evidence](scheduled-local-input-ci-terminal-20261028.json):
all eight required jobs passed against the identical source tree, with 1,513
backend tests, eight disposable TLS transport cases and four Chrome boot
scenarios. The web scenarios cover compatibility and loader boot only; their
T4 catalog and deployment acceptance fields remain false. Unsigned iOS
simulator products are build evidence only. This run does not cover the
subsequent, still-unpublished native date/time and city-selection changes in
this packet; they require their own source and CI verification. Physical Android remains
deferred; signing/store, iOS devices, low-end latency, linguistic/assistive,
hosted/provider, operational, pilot and public acceptance remain separate.
Preserve the Trial-only hosting stop, both volumes, rollback archives and
unapplied TLS/migration packet. Never replay credential/MFA recovery or the
completed bounded S3 probe.
