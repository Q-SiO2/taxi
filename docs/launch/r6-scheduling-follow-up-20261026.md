# Scheduled-service follow-up: reachable bookings and localized states

26 October 2026. Source review against candidate
`5023ffcb9d16fae34893187574786dc57742a0ed`. These are **confirmed source gaps,
not accepted journeys**. They remain within R6/R9; no
hosting purchase, provider, transport enrollment or business-policy change is
needed to implement the existing contracts.

The [label correction](scheduled-localization.md) is now implemented and passes
catalog and JVM/Android compilation checks. Its native/rendered/linguistic gates
remain open. [Pagination is now implemented and locally verified](scheduled-pagination.md);
fresh native/hosted/device acceptance remains open. The findings below retain their
pre-fix source boundary rather than representing accepted current UI behavior.

## Findings

1. **Passenger bookings beyond page one are unreachable.** The backend
   [`list_bookings`](../../backend/src/taximobile_api/domains/scheduled_bookings/router.py)
   accepts page/limit/status, defaults to 20 rows and returns `page`, `limit` and
   `total`. It orders by scheduled time descending and then ID. The
   [client gateway](../../TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/data/scheduling/KtorScheduledBookingGateway.kt)
   sends no page parameter and decodes only `items`; the domain returns a plain
   list. The [passenger sheet](../../TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt)
   renders that list without page navigation. Consequently older or nearer
   bookings can be absent when more than 20 later-scheduled rows precede them;
   those absent rows cannot reach the existing cancellation control. This is a
   source-path finding, not a physical-client reproduction. Driver offer and
   commitment endpoints are **not** paginated in the same way; do not apply this
   finding to them without new evidence.
2. **Lifecycle and cancellation-outcome labels bypass localization.** The passenger
   sheet replaces underscores in the raw booking status, the
   [driver sheet](../../TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt)
   displays raw commitment status, and cancellation outcome is passed raw into a
   localized sentence. Existing localized fare/cancellation-term copy does not
   translate those values. The [backend enum definitions](../../backend/src/taximobile_api/domains/scheduled_bookings/models.py)
   own the actual states; client labels cannot change their semantics or invent
   cancellation/refund success.

## Next bounded implementation

- Preserve the existing bounded page contract in a scheduled-booking page model
  and gateway method. Validate page metadata and duplicate IDs. Use explicit
  previous/next navigation; do not silently fetch an unbounded account history or
  claim that raising the limit removes truncation. Reuse the existing
  [pending-cash page pattern](../../TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/domain/drivers/PendingCashPayments.kt)
  and [shared page controls](../../TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/PendingCashPaymentsSection.kt)
  without mixing financial-work and booking state.
- Keep account/session ownership, loading and stale-response guards. Reset
  navigation when the owner changes; recover deliberately from a page emptied
  by a concurrent change. Refresh server state after a command. Do not send a
  booking/cancellation command merely to refresh or navigate a page.
- Map all seven booking states, four commitment states and four cancellation
  financial outcomes to EN/FR/AR resources, with a conservative explicit unknown
  label. Keep action eligibility server-authoritative and do not map unknown
  values to a successful or cancellable state. Retain RTL and all four styles.
- Verify page two with more than 20 bookings, exact request/page/total retention,
  malformed or mismatched metadata, empty/last pages, owner change, stale response,
  cancellation and ordinary network failures. Cover each known/unknown state label
  and test the rendered pagination/actions with the existing UI harness.
- Run affected shared JVM/Android-host and exact native CI. Update owning API/UI
  docs only to clarify existing behavior; changing server ordering, filtering or
  booking policy requires a separately justified source change. Physical, hosted,
  provider and field acceptance remain separate gates.

The [cancellation packet](journey-cancellation.md) is a distinct preceding fix.
The [Trial stop](staging-capacity-stop-20261026.json) still prevents dependent
hosting work and does not block these source corrections. No launch/GAP gate is
closed by this follow-up packet.
