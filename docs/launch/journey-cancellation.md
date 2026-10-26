# Ride and scheduled-booking coroutine cancellation

26 October 2026. R5/R6 source correction; no backend schema, API, operating policy,
provider, visual identity or hosted configuration change.

## Defect and correction

`KtorRideGateway` and `KtorScheduledBookingGateway` caught coroutine cancellation
inside their general network-error handlers. Reads and estimates surfaced a
network failure, while idempotent booking commands could enter their retry block
after the caller had cancelled. Cancellation during the second attempt was also
converted into a network failure. The existing coordinator already propagates
cancellation rather than turning it into product state.

Both gateways now rethrow `CancellationException` before general exception
handling in reads, the first command attempt and its one permitted retry. The
existing same-key retry remains for ordinary transport failures. This changes
neither server-side idempotency nor the driver's/passenger's business commands.

Cancelling a coroutine is not an authoritative cancellation of a ride or booking,
nor proof that the server rejected a request already sent. Preserve that unknown
outcome and reload authorized server state when the owning flow resumes. Do not
automatically invent a new command or success state after cancellation. Durable
process-death/unknown-result/device acceptance remains separately required.

## Verification boundary

The new common `RideSchedulingCancellationTest` uses actual Ktor request pipelines
with a deterministic engine and synthetic identities, never a live provider.
The predecessor reproduces **nine failures out of ten tests**. The first corrected
JVM run passes all ten. Cases cover scheduled list/estimate, point-to-point and
fixed-route creation, scheduled acceptance, second-attempt booking cancellation,
fixed-route catalog/create, second-attempt immediate creation, and the retained
bounded ordinary-network retry. Same-command retry checks include exact URL,
method, idempotency key and serialized body.

The affected data/coordinator JVM regression passes **109 tests**, zero
failures/errors/skips, including the exact serialized-body checks. The same
selection passes **128 Android-host tests**. The [verification record](journey-cancellation-verification-20261026.json)
binds final source hashes and retained failed/passing reports. Fresh native
successor CI is still required for the final source. [CI 238](runtime-preservation-ci-terminal-20261026.json)
accepts the predecessor, not these mobile changes. Actual Android/iOS lifecycle,
provider, hosted and field acceptance remain open. The existing
[Trial capacity stop](staging-capacity-stop-20261026.json) remains binding.
