# Driver scheduled-offer review and response expiry

26 October 2026. R6/R9 source successor to `b1be457`. This corrects driver-side
review gaps; it does not close the scheduled-service or real-world launch gate.

## Confirmed baseline and contract

Four rendered baseline cases reproduce three defects: unknown refund mode uses
non-refundable copy, and expired or invalid response timing leaves Accept
enabled. The positive current-offer control passes. The preserved baseline is
`.tools/real-world-launch/scheduled-driver-baseline-20261026.zip`.

[UI requirements](../ui.md) require honest offer expiry and sufficient financial
review; [design](../design.md) requires driver choice and backend authority.
The API returns `expires_at` and `server_time` per scheduled offer, without an
issued-at timestamp. Its list is independently driver-authorized and filters
pending, currently unexpired offers for an offering booking. Acceptance locks
and rechecks server expiry, eligibility and conflicts. These server rules remain
unchanged; a UI timer cannot create a commitment or determine a conflict.

## Source correction

- Share one localized cancellation-term presentation between passenger and
  driver. Exact supported modes and valid cutoffs retain their meanings;
  unknown values cannot become non-refundable promises. Drivers can explicitly
  decline unsupported terms; the review guard must not force acceptance or make
  them online.
- Anchor scheduled response review to a monotonic mark captured before the
  owned list request. Count request/response delay conservatively, and retain
  the anchor through copies, recomposition and sheet reopening. Use the server's
  expiry-minus-server-time envelope and elapsed duration, with ceiling seconds.
  Do not use the device wall clock, count timer callbacks as elapsed time, invent
  an issued timestamp or change the server deadline. Invalid/unrepresentable
  timing is unavailable; local zero only disables acceptance and requests a read.
- Refresh once per expired/invalid offer ID while the sheet retains it; repeated
  invalid envelopes must not produce an automatic refresh loop. Offer a localized
  explicit refresh control, preserving its accessible name while pending.
- Accept requires pending status, a supported service and financial review, and
  a nonexpired envelope. Recheck at click. The coordinator independently reloads
  the owned offers and requires exactly one selected ID with supported review.
  Only this read may recover the session once; recheck local owner after it.
  Failed/cancelled reads, logout/replacement and unsupported/missing/duplicate
  offers cannot send acceptance. Do not session-replay an acceptance rejection.
  Keep explicit decline and post-command authoritative readback.
- Localize the service badge rather than printing a transformed raw enum.
  Preserve all four identities, EN/FR/AR, and static Notepad. The countdown is
  functional status, not an elaborate animation. No schema, endpoint, business
  policy, dependency, grant, provider or hosting change.

## Verification and continuation

[Exact-source local evidence](scheduled-driver-review-verification-20261026.json)
records **179 affected JVM cases**, **178 Android-host cases**, and both Android
role Kotlin compilations passing. The JVM set includes seven driver and six
passenger/pagination rendered cases; driver unknown-term review is covered across
all 12 language/style combinations. It verifies explicit decline, disabled
acceptance, monotonic expiry, one automatic refresh, explicit retry and the
pending control's accessible purpose. The suspended-read expiry race also passes.
These sets overlap and must not be added into a unique-test total. The initial
112-case pass and three-failure rendered baseline remain preserved.

All 15 owned source hashes are captured. Catalogs validate 1,290 keys each;
the mobile contract validates 85 existing HTTP operations and one WebSocket.
All 458 backend Python inputs match the predecessor. Publish the bounded
successor on draft PR 74; its own native CI must accept that source.

The passenger predecessor passes [CI 246](scheduled-cancellation-review-ci-terminal-20261026.json):
all eight required jobs, 1,482 backend cases and eight disposable TLS probes with
cleanup. Verified artifact digests bind its tested merge to its source tree.
This does not accept this later driver implementation, actual devices, signed
distribution, hosted providers or operational/field journeys. Keep the owner's
source-only continuation and [Trial stop](staging-capacity-stop-20261026.json).

Further confirmed presentation work remains: scheduled pickup/protected-window
rows still print raw timestamp strings instead of the required city-local time
and timezone. The [immediate-offer correction](immediate-offer-review.md) now owns
the separate callback-count timing and cancellation defects. This scheduled
packet does not close their device/background or timezone acceptance.

Published source `9b656d9` passes [CI 248](scheduled-driver-review-ci-terminal-20261026.json)
across all eight required jobs and 1,482 backend cases, including eight disposable
TLS probes and cleanup. Artifact digests bind the tested merge to the same source
tree; both unsigned iOS simulator products build. The [earlier observation](scheduled-driver-review-ci-observation-20261026.json)
is retained. These results cannot accept the later immediate-offer, verifier or
city-time source, actual devices, signing, providers, hosted or field behavior.
