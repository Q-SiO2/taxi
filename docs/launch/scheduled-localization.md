# Scheduled booking and commitment labels

26 October 2026. R6/R9 source implementation following the
[confirmed scheduling gaps](r6-scheduling-follow-up-20261026.md).

The passenger booking pill and driver commitment pill now resolve backend states
to shared resource identities. Passenger cancellation outcomes also resolve
through the catalog before entering the localized outcome sentence. Raw English
enum codes no longer serve as those labels.

The mapper covers seven booking states, four commitment states and four financial
outcomes. Seventeen new keys in each English/French/Arabic catalog include explicit
unknown-state and unknown-financial-status labels. `LIVE_RIDE_CREATED` reads
“Trip created”; it does not claim that a driver arrived or that travel started.
Pending refunds remain pending, and a released commitment does not become a
fulfilled one. Existing server state still controls cancellation eligibility and
all financial transitions. The shared mapping introduces no new product state.

The [final verification record](scheduled-localization-verification-r2-20261026.json)
binds the two screen files, shared mapper and three catalogs. The catalog gate
validates **1,279 entries per language**, exact keys and placeholders; its three
unit tests pass. Shared JVM and Android compilation pass. A CRLF insertion-format
correction is retained and the final source recompiles successfully. Existing
unrelated compiler warnings remain. A distinct cancelled-commitment label preserves
French/Arabic agreement; the earlier 16-key compiled record is retained separately.

This is source/catalog/compilation evidence. Fresh successor native CI, rendered
screen coverage across all four styles, linguistic review, RTL/assistive
technology and actual devices remain separate requirements. The owner again
selected source continuation on 26 October; no phone was connected at the device
inventory check. [CI 240](journey-cancellation.md) belongs to the preceding
cancellation candidate and cannot accept these later labels automatically.

Passenger booking pagination remains the other confirmed R6 follow-up. This
presentation fix does not make records beyond the first page reachable, close
R6/R9 or reopen the [Trial hosting gate](staging-capacity-stop-20261026.json).
