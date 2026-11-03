# Immediate-offer elapsed time, cancellation and unavailable review

26 October 2026. R5/R9 successor to driver scheduled-review candidate `9b656d9`.
This packet does not close physical/background, dispatch or launch acceptance.

## Confirmed baseline

The immediate-offer card increments an elapsed-seconds counter after each timer
callback and restarts it when the card is recreated. A delayed callback can leave
Accept enabled after the actual elapsed window. The gateway also converts caller
coroutine cancellation into a network failure on read, Accept and Decline. The
valid-offer control passes after the test scrolls the action into the viewport;
the corrected five-case baseline reproduces four product failures. Both the
original viewport observation and corrected baseline archives are preserved.

[Matching](../matching.md) and [UI](../ui.md) keep expiry/assignment on the server,
and require disabled acceptance plus a refresh for local zero or unavailable
timing. This correction follows those rules without new business policy.

## Implemented behavior

- `DriverRideOffer` retains a monotonic request-start mark. The gateway captures
  it before the owned list request, so token/read/transport delay counts
  conservatively. Copies and card reopening retain it; timer callbacks sample
  elapsed duration rather than representing elapsed seconds themselves.
- The existing countdown uses the exact supplied expiry, issued timestamp and
  list server time. It ceilings fractional seconds, keeps progress in 0–1 and
  rejects malformed, nonpositive or unrepresentable windows and invalid elapsed
  duration. Retain the existing explicit-seconds helper overload for callers.
  The real backend captures `server_time` before querying rows: an offer issued
  concurrently after that time is not rejected merely for that ordering. No
  device wall clock, invented deadline, client assignment or availability change.
- Disable Accept on local expiry, invalid timing, unsupported service or a
  pending action; recheck the clock at the tap. Unknown service cannot silently
  become an on-demand label. Keep explicit confirmed Decline available.
- Request one automatic refresh per offer ID while the card remains mounted;
  repeated invalid responses do not create an automatic loop. Keep a localized
  explicit refresh action, disabled while pending. Labels request refresh instead
  of claiming an ongoing refresh after a read failed or returned invalid data.
  The card remains disabled until an authorized list update removes/replaces it.
- Accept, Decline and refresh retain their accessible purpose when spinners
  replace visible labels. All four styles, EN/FR/AR and static Notepad remain.
- Rethrow coroutine cancellation before generic network normalization in all
  immediate-offer gateway paths. Ordinary transport failures retain their single
  attempt; do not introduce command replay or claim a cancelled request proves
  the server rejected an action. Existing server locks, expiry, eligibility,
  financial snapshots and post-command readback remain authoritative.

No backend, schema, endpoint, dependency, privilege, provider or hosting change.

## Verification and continuation

[Exact-source local evidence](immediate-offer-review-verification-20261026.json)
records **225 affected JVM cases**, **181 Android-host cases**, and both Android
role Kotlin compilations passing. The JVM set includes eight immediate-offer
rendered cases and critical/scheduled-driver regressions. Expired review and
explicit refresh are checked in all 12 language/style combinations. The tests
cover independent elapsed/UI clocks, reopening, one automatic refresh, explicit
retry, unavailable service, confirmed decline and pending accessible purpose.
These sets overlap; do not sum them into a unique-test total.

All 13 owned source hashes are captured; all 458 backend Python inputs match
the predecessor. Catalogs validate 1,292 entries each and the mobile contract
validates 85 existing HTTP operations and one WebSocket. The initial 13-case
pass and both baseline/viewport observations remain preserved. Publish the
bounded successor on draft PR 74; its own immutable native CI must accept it.

Scheduled city-local pickup/protected-window presentation remains a separate
confirmed source follow-up. Physical timing/background/lock/process-death,
assistive/linguistic review, signed distribution, provider/hosted operation and
staffed pilot/public acceptance remain open. The owner's source-only continuation
and [Trial capacity stop](staging-capacity-stop-20261026.json) still apply.

Published source `e38ae7b` failed [CI 250](immediate-offer-review-ci-terminal-20261026.json)
at the mobile Python source gate; Android packaging/minification was skipped.
The [focused source-gate correction](immediate-offer-source-gate.md) owns the fix
and now passes all eight jobs in [CI 252](immediate-offer-source-gate-ci-terminal-20261026.json).
The [earlier observation](immediate-offer-review-ci-observation-20261026.json)
is retained. Scheduled-driver predecessor [CI 248](scheduled-driver-review-ci-terminal-20261026.json)
now passes all eight required jobs for its own source; it cannot accept this
immediate-offer successor or its later corrections.
