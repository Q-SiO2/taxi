# Reachable passenger scheduled bookings

26 October 2026. R6 source implementation against the existing paginated API.
Status: **local gateway/coordinator/rendered checks pass; successor native CI and
hosted/device/field acceptance remain open**.

The passenger can now navigate beyond the first twenty bookings. Each explicit
page selection sends one authenticated GET with `page` and `limit=20`; the client
preserves the server's ordering, items and page/total metadata. The shared domain
page rejects invalid counts, missing/blank or duplicate IDs and mismatched page
boundaries. Malformed JSON and Ktor conversion failures become a fixed actionable
read failure, without exposing response contents or retrying a booking command.

Page selection is local navigation, scoped to the session owner. Login/logout
reset it. Read revisions reject a late page after a newer read, and owner checks
prevent an old response from painting after session replacement. Token recovery
can repeat the authorized read once; it cannot replay creation or cancellation.
Ordinary refresh retains the selected page and reloads all visible authoritative
state. An empty page beyond the new last page performs at most one corrective
read, never an unbounded history scan.

The shared passenger sheet exposes localized Previous/Next, page context and
retry controls. A failed read removes stale booking rows without presenting an
empty collection as success or hiding a freshly read live ride. Pending controls
are disabled, show progress and retain their accessible names. Changing page or
losing the selected row closes its cancellation confirmation; confirmation still
sends only the selected ID and refreshes the backend result. Cancellation terms,
financial outcome, driver commitment and eligibility remain server-owned.

## Evidence and limits

The [verification record](scheduled-pagination-verification-20261026.json) binds
21 source/test/catalog inputs and retained observations. Final affected checks
pass **145 JVM tests**, **156 Android-host tests**, and **five rendered UI tests**.
One rendered case exercises navigation in **all 12 language/style combinations**:
English/French/Arabic and Folded Streets/Street Press/Glazed Machine/Notepad.
The two Android role entrypoints compile. Catalog validation covers **1,285 keys
per language** with matching placeholders. These sets overlap; do not add them
into a misleading unique-test total.

Failed compilation/test/observer records remain: an old quote fake needed the
new page signature, test initialization needed Unit, the active-ride fake needed
its list read, navigation needed the actual map/search mode, and malformed JSON
required Ktor's conversion exception. The pending button's replaced visual label
then exposed its missing accessible name; the final rendered check verifies the
disabled action by that name. No business command or restore was repeated to
hide an observer failure.

[CI 240](journey-cancellation-ci-terminal-20261026.json) and
[CI 242](scheduled-localization-ci-terminal-20261026.json) now accept their own
predecessor sources across all eight required jobs and 1,458 backend cases each.
They do not accept this later pagination implementation. Fresh complete native
CI remains required; no hosted migration, provider, price/financial rule,
dependency, schema, permission or real-participant change is part of this packet.
Actual devices, assistive technology, operator/linguistic review, signed release,
hosted operation and field acceptance remain open. The owner's source-only
continuation and [Trial capacity stop](staging-capacity-stop-20261026.json) persist.

## Further scheduled-service review

This closes the confirmed source truncation path, not R6 or the whole launch.
The passenger cancellation-term helper still uses its non-refundable text for an
unrecognized refund mode; that is a separate confirmed source follow-up. Compare
it with the existing strict known-mode web presentation and retain an explicit
unknown/unavailable review state rather than guessing a financial policy.
