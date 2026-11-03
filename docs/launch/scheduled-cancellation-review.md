# Scheduled cancellation terms: explicit supported review

26 October 2026. Source successor to pagination candidate `1f8bfb9`. This is
R6/R9 engineering; it does not close a launch, physical, provider or money gate.

## Confirmed problem

The shared passenger helper and both backend response helpers treated every
unrecognized surcharge-refund mode as non-refundable. That silently assigned a
financial meaning to a future or malformed value. The existing web presentation
already recognizes only the three exact known modes and shows unavailable copy
for another mode. The backend financial service strictly converts the enum;
its actual refund calculation is unchanged by this correction.

## Implemented boundary

- Render the exact meanings of `ALWAYS_FULL`, `FULL_BEFORE_CUTOFF` and
  `NON_REFUNDABLE`. A cutoff outside the existing policy contract's 0–10,080
  minutes, or an unknown mode, produces unavailable terms. Preserve raw response
  metadata for compatibility; do not display raw codes or an untrusted summary
  as a substitute financial promise.
- Shared passenger review has English, French and Arabic unavailable copy.
  Creation confirmation and cancellation confirmation are disabled for an
  unsupported review. The coordinator independently prevents these commands
  from proceeding through that state. The compatibility flag is a review guard,
  never authorization or a client refund calculation.
- Cancellation reads the selected booking from the existing independently
  authorized `GET /scheduled-bookings/{id}` endpoint before sending its command.
  It does not infer ownership from the current page. Validate the returned ID;
  retain unknown terms so the review guard can reject them. Only the read may
  recover the session once. Recheck local session ownership after the read;
  logout/replacement, failed reads and cancellation cannot send a command.
  The existing idempotent command transport and backend financial authority
  remain unchanged. An authentication rejection of the command is not replayed
  by session recovery.
- Both backend response helpers share the explicit presentation decision. No
  schema, endpoint, permission, rate, actual refund rule or infrastructure change.

## Verification and continuation

The preserved backend baseline reproduces 12 failures in 18 cases. After the
correction, 24 focused and 90 affected scheduling/pricing unit cases pass; these
sets overlap. Localization validates 1,286 keys in each catalog. The expanded
mobile contract validates 85 existing HTTP operations and one WebSocket.

[Exact-source local verification](scheduled-cancellation-review-verification-20261026.json)
passes **97 JVM cases** (including six rendered UI cases), **88 Android-host
cases**, and both Android role Kotlin compilations. The rendered suite checks
unknown-terms disabled cancellation in all 12 language/style combinations;
pagination rendering is retained. These sets overlap and are not a unique-test
total. The 16 owned source hashes and affected backend evidence are recorded.
Failed compilation/assertion observations are preserved: the test fixture needed
valid List destructuring and the existing `/api/v1` request prefix. No product
regression was hidden by those test corrections.

Publish the bounded successor on draft PR 74. Its fresh immutable CI must accept
this source; predecessor CI cannot be borrowed.

The [pagination packet](scheduled-pagination.md) and its CI belong to the
preceding source. Hosted deployment, device/assistive-technology/linguistic
acceptance, signing/distribution, staffed operation and field journeys remain
open. The [Trial capacity stop](staging-capacity-stop-20261026.json) and the
owner's instruction to continue source work remain in force. Do not apply the
prepared TLS deployment or replay credentials, storage probes or business
commands to obtain evidence.

Published source `b1be457` passes [CI 246](scheduled-cancellation-review-ci-terminal-20261026.json)
across all eight required jobs and 1,482 backend cases, including eight disposable
TLS probes and cleanup. Artifact digests bind the tested merge to the same source
tree; both unsigned iOS simulator products build. The [earlier observation](scheduled-cancellation-review-ci-observation-20261026.json)
is retained. The [driver review successor](scheduled-driver-review.md) addresses
the separate remaining driver fallback and expiry controls. This passenger CI
does not accept that successor or hosted/physical/operational/field behavior.
