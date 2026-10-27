# Bind scheduled review to the requested trip

27 October 2026. R6/R9 source packet following the packaging candidate
`53d6531`, whose own [CI 256](scheduled-city-time-packaging-ci-terminal-20261027.json)
passes all eight required jobs. That result does not accept this later source.
The full [R0-R12 goal](../real-world-launch.md), domain rules and T0-T10 gates remain.

## Confirmed failure

The passenger sheet tracked a local reviewed-input key, but did not compare the
returned estimate with those inputs. Requesting a review for day B could expose
the retained estimate for day A and an enabled confirmation. Direct coordinator
calls also accepted an estimate for a different day or fixed-route direction.
Unchanged policy version numbers cannot establish which trip the passenger saw.

The corrected three-case regression baseline fails in all three places: the
sheet exposes confirmation and each coordinator sends one command instead of
zero. The first baseline only discovered the UI case because two expression-body
coroutine tests inferred a non-Unit return. Their assertions were corrected to
make the test methods discoverable; both observations are retained separately.

## Existing-contract correction

A shared predicate compares the requested and returned instant, service type and
context before displaying review, publishing a read response or creating a
booking. Point requests bind the exact finite, in-range coordinate pair and the
requested city when one is supplied. Server-normalized address labels do not
change coordinate identity. Fixed-route requests bind the immutable direction
version and validate resolved coordinates. Unknown service/payment context,
missing city/operator identifiers and malformed times fail closed.

UTC normalization is accepted when the instant is identical. Submission retains
the original explicit-offset input and the exact server-returned economics and
policy versions. The backend still owns pricing, membership, eligibility,
lead-time, availability and booking creation. No schema, endpoint, dependency,
quote token, automatic mutation retry or client fare calculation is introduced.
The synthetic point fixture now uses the backend's existing `ON_DEMAND` service
value rather than the obsolete `POINT_TO_POINT` label.

An unmatched retained review hides its price and confirmation. Localized copy
asks the passenger to review time, route and price again. Explicit review can
recover with a matching response. The UI checks again on confirmation and the
coordinator provides an independent command boundary. Existing unavailable-time,
unsupported-refund, authentication recovery and cancellation behavior remains.

## Verification and continuation

The [source-hash checkpoint](scheduled-review-binding-verification-20261027.json)
records the corrected failing baseline, affected shared/rendered tests, Android
host tests, role builds, source-tool checks and catalog validation. Test sets
overlap and must not be summed as a readiness score. Large-text warning coverage
uses EN/FR/AR and all four styles; captured desktop Compose renders are not
physical Android or linguistic acceptance.

Local verification passes 204 affected JVM tests, 374 Android-host tests, both
debug role APK builds and 121 source/build-tool tests. The three catalogs validate
1,295 entries each. The twelve warning renders use 200% text in a 360 × 800 dp
viewport; Arabic Folded Streets and French Notepad captures were visually
inspected. The initial platform invocation named a nonexistent Gradle project and
ran no compilation/tests; its corrected role tasks pass without a source change.

Run fresh immutable CI for this candidate, including minified Android identity,
iOS simulator products and production web size/boot under the unchanged caps.
The prior candidate's CI cannot satisfy those gates. Continue the
[friendly city-local scheduling input](scheduled-city-time.md#next-bounded-source-packet-scheduling-input)
after the request/review boundary is verified. That input remains manual RFC3339
and this packet does not claim the picker complete.

Physical Android remains deferred by the owner. Preserve the recorded Trial
hosting stop, rollback archives, both volumes and the unapplied TLS/migration
packet. No paid upgrade, credential/MFA replay, real document/participant/money
action, pilot or public activation follows from this source work.
