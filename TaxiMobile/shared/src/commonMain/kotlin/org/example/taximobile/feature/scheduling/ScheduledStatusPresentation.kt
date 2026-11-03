package org.example.taximobile.feature.scheduling

import org.jetbrains.compose.resources.StringResource
import taximobile.shared.generated.resources.*

/** Display labels only; server state and command eligibility remain authoritative. */
fun scheduledBookingStatusLabel(status: String): StringResource = when (status) {
    "SCHEDULED" -> Res.string.scheduled_state_scheduled
    "OFFERING" -> Res.string.scheduled_state_offering
    "DRIVER_COMMITTED" -> Res.string.scheduled_state_driver_committed
    "DISPATCH_HANDOFF" -> Res.string.scheduled_state_dispatch_handoff
    "LIVE_RIDE_CREATED" -> Res.string.scheduled_state_live_ride_created
    "UNFULFILLED" -> Res.string.scheduled_state_unfulfilled
    "CANCELLED" -> Res.string.scheduled_state_cancelled
    else -> Res.string.scheduled_state_unknown
}

fun scheduledCommitmentStatusLabel(status: String): StringResource = when (status) {
    "ACTIVE" -> Res.string.scheduled_commitment_active
    "RELEASED" -> Res.string.scheduled_commitment_released
    "FULFILLED" -> Res.string.scheduled_commitment_fulfilled
    "CANCELLED" -> Res.string.scheduled_commitment_cancelled
    else -> Res.string.scheduled_state_unknown
}

fun scheduledFinancialOutcomeLabel(outcome: String): StringResource = when (outcome) {
    "NO_CHARGE" -> Res.string.scheduled_outcome_no_charge
    "SURCHARGE_RETAINED" -> Res.string.scheduled_outcome_surcharge_retained
    "REFUND_PENDING" -> Res.string.scheduled_outcome_refund_pending
    "REFUNDED" -> Res.string.scheduled_outcome_refunded
    else -> Res.string.scheduled_outcome_unknown
}
