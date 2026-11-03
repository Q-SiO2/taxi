package org.example.taximobile.feature.scheduling

import androidx.compose.runtime.Composable
import org.example.taximobile.domain.scheduling.ScheduledCancellationTerms
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

/** One financial review presentation for passenger and driver; never use raw summary copy. */
@Composable
internal fun ScheduledCancellationTerms.localizedSummary(): String = when {
    !isSupportedForReview -> stringResource(Res.string.scheduled_refund_unavailable)
    surchargeRefundMode == "ALWAYS_FULL" -> stringResource(Res.string.scheduled_refund_always_full)
    surchargeRefundMode == "FULL_BEFORE_CUTOFF" -> stringResource(Res.string.scheduled_refund_before_cutoff, passengerCancelCutoffMinutes)
    else -> stringResource(Res.string.scheduled_refund_never)
}
