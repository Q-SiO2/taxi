package org.example.taximobile.feature.scheduling

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import org.example.taximobile.domain.scheduling.ScheduledBookingPage
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.isPending
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
internal fun ScheduledBookingPageControls(
    page: ScheduledBookingPage?,
    unavailable: Boolean,
    requestedPage: Int,
    pendingAction: AppAction?,
    onPage: (Int) -> Unit,
) {
    if (unavailable) {
        Text(stringResource(Res.string.message_scheduled_bookings_unavailable))
        val label = stringResource(Res.string.scheduled_page_reload)
        TaxiButton(label, { onPage(requestedPage) }, modifier = Modifier.semantics { contentDescription = label },
            enabled = pendingAction == null,
            loading = pendingAction.isPending(AppActionKind.LOAD_PASSENGER_SCHEDULED_BOOKINGS, requestedPage.toString()))
        return
    }
    if (page == null || page.total == 0) return
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
        Text(stringResource(Res.string.scheduled_page_summary, page.page, page.total))
        val previousLabel = stringResource(Res.string.scheduled_page_previous)
        val nextLabel = stringResource(Res.string.scheduled_page_next)
        if (page.hasPrevious) TaxiButton(previousLabel, { onPage(page.page - 1) },
            modifier = Modifier.semantics { contentDescription = previousLabel },
            enabled = pendingAction == null, style = TaxiButtonStyle.Secondary,
            loading = pendingAction.isPending(AppActionKind.LOAD_PASSENGER_SCHEDULED_BOOKINGS, (page.page - 1).toString()))
        if (page.hasNext) TaxiButton(nextLabel, { onPage(page.page + 1) },
            modifier = Modifier.semantics { contentDescription = nextLabel },
            enabled = pendingAction == null, style = TaxiButtonStyle.Secondary,
            loading = pendingAction.isPending(AppActionKind.LOAD_PASSENGER_SCHEDULED_BOOKINGS, (page.page + 1).toString()))
    }
}
