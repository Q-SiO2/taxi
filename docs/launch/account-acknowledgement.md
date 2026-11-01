# Signed-out account acknowledgement — 1 November 2026

R9/GAP-025 covers the actual signed-out account states, not just their atlas
compositions. The shared screen rendered a successful registration as a polite
announcement, but it rendered a completed password change and the conditional
offline-code recovery acknowledgement as assertive danger messages. The
coordinator already supplied a distinct `recoveryCompleted` state and cleared
secret fields; only the presentation tone was wrong.

Two rendered JVM regressions reproduced the false error announcements before
the fix. The screen now treats `recoveryCompleted` as informational and polite.
The recovery copy remains conditional: acceptance of the request does not
confirm account existence, code validity or an actual password change. Failed
requests remain assertive errors. The existing registration success and failure
checks remain in the same focused class. Its final 42 tests pass, with zero
failures or errors. An intermediate test-selector failure matched both visible
"Sign in" controls; the corrected check targets the submit control and is
retained in the local test report history.

This is source/rendered-JVM evidence for S05/S07/S08/S15. Four-style, EN/FR/AR,
device assistive-technology, background/secret lifecycle and signed-release
acceptance remain separate R9/R10 gates. A fresh immutable CI run is required
for the new source head. No authentication, account enumeration, API or backend
authorization rule changes.
