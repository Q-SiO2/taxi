# Scheduled city-local time

26 October 2026. R6/R9 source packet; successor to the immediate-offer verifier
repair. `operations.md` already requires city-local presentation and UTC server
timestamps. Passenger booking rows and driver commitments previously exposed raw
timestamps, and the passenger quote omitted the reviewed pickup time. A retained
three-case rendered baseline demonstrates those failures.

The shared formatter now resolves the backend's named city timezone for each
instant. Pickup review, upcoming bookings, cancellation confirmation, driver offers
and protected commitment windows show an ISO date, 24-hour local time and actual
UTC offset. Seconds and fractional seconds remain when present. Repeated local
hours retain distinct offsets; window ordering is checked against the original
instants. EN/FR/AR resources and directional isolation keep this compact display
readable in RTL. Booking and offer headers wrap vertically at large text sizes.

Invalid instants or unrecognized named zones show a localized unavailable message;
there is no device-time or fixed-offset fallback. Passenger quote confirmation and
driver acceptance require interpretable pickup timing. Existing bookings expose a
bounded page reload. Explicit cancellation remains available under the existing
known cancellation terms, including when display timing is unavailable. No new
client-side deadline, tariff, refund, assignment or financial authority is added.
This display conversion does not rewrite existing timestamp command payloads.

## Dependency and platform decision

No existing dependency supplied named timezone rules across all five shared
targets. Use pinned `kotlinx-datetime` 0.8.0 for this core requirement, retaining
`kotlin.time.Instant`. Its [official pinned documentation](https://raw.githubusercontent.com/Kotlin/kotlinx-datetime/v0.8.0/README.md)
describes city-zone conversion, browser timezone initialization and Android
desugaring. Android keeps minSdk 24 and enables `desugar_jdk_libs` 2.1.5; packaging
and device checks must establish support rather than assuming a JVM pass proves it.

Both browser graphs initialize `@js-joda/timezone` 2.26.0. Its [registry peer
contract](https://registry.npmjs.org/@js-joda/timezone/2.26.0)
requires core >=5.7.0, so both Yarn roots resolve one pinned
`@js-joda/core` 5.7.0, with regenerated locks. The datetime library's older core
request produces an explicit resolution warning; both actual browser runtimes
must pass seasonal, repeated-hour and subsecond cases. This is a dependency
compatibility decision, not a second date/time authority. Keep timezone-data
updates deliberate and tested; device/OS rules and bundled browser data can age.
The selected browser package bundles tzdb 2026a; the library's native build uses
2026b, while JVM/Android use their runtime rules. Moroccan seasonal/repeated-hour
fixtures must agree across targets; this does not promise permanently identical
future rules without updates.

The first production JS output reached **7,877,300 bytes**, above the unchanged
7,000,000-byte cap, because an exported initialization value retained the entire
timezone module in the operations console. Its output/hash and failed build log
are retained. Only that run's verified Wasm optimizer process was deliberately
stopped after the size defect was established; that incomplete distribution is
not packaging evidence. A thin platform initializer now makes module retention
follow actual formatter use. Native initializers defer to the existing runtime;
JS/Wasm reference the side-effect module without inventing a provider export.
Both browser tests and production size/boot must pass again for this correction.

## Verification and remaining gates

The initial source's shared regression run passes 170 affected JVM cases, including six
pure time cases, eight city-time rendered cases, coordinator creation guards and
existing critical-state, immediate-offer, scheduled-driver and pagination UI. The rendered
suite checks all twelve language/style combinations at 200% text and a 360-pixel
viewport. Actual Arabic Folded Streets and English Notepad captures were inspected.
Android host tests pass 363 cases and both debug role APKs assemble. JS and Wasm
each pass 86 browser cases. The three catalogs validate 1,294 entries each.
The [source-hash checkpoint](scheduled-city-time-verification-20261026.json)
explicitly leaves minified Android and complete web packaging/boot pending.
These sets overlap; they are not a launch
readiness percentage.

Failed observations remain retained: the three-case baseline, two intermediate
UI harness failures caused by a prefilled quote bypassing map selection, and an
initial browser test exceeding Mocha's unchanged 2-second timeout. The diagnostic
successor measured a first lookup of 1,283 ms in JS and 276 ms in Wasm; after the
initializer correction these were 1,459 ms and 186 ms on this machine.
These are observations, not latency acceptance or a field-device SLO.
No timeout was raised. Minified Android packaging, complete production web size/boot and
fresh immutable native CI remain required before this packet is accepted. The
corrected raw JS output is **6,953,397 bytes**, within the unchanged 7 MB cap;
the complete compatibility distribution must still pass its own checks. The
review candidate may be published to start clean CI while local optimization
continues, with these pending gates recorded explicitly. Complete
packaging acceptance cannot be inferred from the shared tests or raw JS size.

The published `2e9275a` source subsequently fails [CI 254](scheduled-city-time-ci-terminal-20261026.json)
at the complete Wasm size check and Android artifact-verifier step, despite
successful browser/shared tests and minified builds. The [packaging repair](scheduled-city-time-packaging.md)
owns those fixes and fresh verification, including the explicit provider-only
test startup allowance. The earlier source-hash checkpoint remains historical.

The manual RFC3339 scheduling input still needs a friendly city-local picker;
this packet fixes review/presentation and does not claim that input task complete.
Actual low-end Android, named-zone data freshness, EN/FR/AR linguistic review,
iOS device/runtime, lifecycle and staff/hosted/field acceptance remain open.
Continue source work under the owner's device deferral. Trial capacity and the
unapplied hosted TLS/migration packet remain separate gates. No purchase, resource
deletion, credential/MFA replay, participant, real-money or public activation.

## Next bounded source packet: scheduling input

Replace manual RFC3339 entry using the existing public city timezone metadata
(`PublicRideCity.timezone`), with a compact date/time control and visible city
context. Establish these cases before selecting the conversion implementation:

1. Ordinary point and fixed-route dates produce one explicit instant, preserving
   the selected city/route and obtaining a fresh backend price/terms review.
2. Nonexistent local clock times are rejected with an actionable adjustment;
   repeated hours require an explicit offset choice. No silent gap shift or
   ambiguous-hour default may become a booking.
3. Unknown or changed city/timezone metadata, route changes, retries and delayed
   quote responses cannot confirm an estimate for a different request. Commands
   retain backend pricing/eligibility/lead-time authority and are not replayed.
4. Typed input and clear correction/recovery work in EN/FR/AR/RTL, all four styles
   and large text. Cover the Moroccan seasonal transition fixtures and actual
   phone keyboard/picker behavior when device testing resumes.

This is a follow-up acceptance packet, not a claim that the input conversion or
its full platform/device behavior has already been implemented.
