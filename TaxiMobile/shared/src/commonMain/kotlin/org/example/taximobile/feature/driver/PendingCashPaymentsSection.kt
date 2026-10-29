package org.example.taximobile.feature.driver

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.key
import org.example.taximobile.domain.drivers.PendingCashPayment
import org.example.taximobile.domain.drivers.PendingCashPaymentsPage
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.isPending
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.components.TaxiCard
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

/** The server queue is the sole source of these controls, never history/earnings. */
@Composable
internal fun PendingCashPaymentsSection(
    queue: PendingCashPaymentsPage?,
    unavailable: Boolean,
    pendingAction: AppAction?,
    onSelect: (PendingCashPayment) -> Unit,
    onPage: (Int) -> Unit,
) {
    if (unavailable) {
        Text(stringResource(Res.string.message_pending_cash_unavailable))
        TaxiButton(stringResource(Res.string.retry_pending_cash), { onPage(1) }, enabled = pendingAction == null)
        return
    }
    if (queue == null || queue.total == 0) return
    Text(stringResource(Res.string.pending_cash_title), style = MaterialTheme.typography.titleMedium)
    val queueSummary = if (queue.total == 1) {
        stringResource(Res.string.pending_cash_single)
    } else {
        stringResource(Res.string.pending_cash_count, queue.total)
    }
    Text(queueSummary, style = MaterialTheme.typography.bodySmall)
    queue.items.forEach { payment ->
        key(payment.paymentId) {
            TaxiCard {
                Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    Text("${payment.amount} ${payment.currency}", style = MaterialTheme.typography.titleMedium)
                    Text(stringResource(Res.string.pending_cash_date, (payment.completedAt ?: payment.createdAt).take(10)), style = MaterialTheme.typography.bodySmall)
                    TaxiButton(
                        stringResource(Res.string.confirm_cash_received),
                        { onSelect(payment) },
                        enabled = pendingAction == null,
                        loading = pendingAction.isPending(AppActionKind.SETTLE_DRIVER_CASH, payment.rideId),
                    )
                }
            }
        }
    }
    if (queue.hasPrevious) TaxiButton(stringResource(Res.string.pending_cash_previous), { onPage(queue.page - 1) }, enabled = pendingAction == null, style = TaxiButtonStyle.Secondary)
    if (queue.hasNext) TaxiButton(stringResource(Res.string.pending_cash_next), { onPage(queue.page + 1) }, enabled = pendingAction == null, style = TaxiButtonStyle.Secondary)
}
