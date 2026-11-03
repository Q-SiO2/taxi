package org.example.taximobile.feature.ui.components

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.foundation.layout.heightIn
import androidx.compose.ui.unit.dp
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
fun OfferCard(
    pickupSummary: String,
    distanceAndEta: String?,
    fare: String?,
    /** Backend-authored fare/settlement facts; this component performs no math. */
    details: List<String> = emptyList(),
    expiryLabel: String,
    expiryFraction: Float? = null,
    acceptEnabled: Boolean = true,
    declineEnabled: Boolean = true,
    acceptLoading: Boolean = false,
    declineLoading: Boolean = false,
    onAccept: () -> Unit,
    onDecline: () -> Unit,
    modifier: Modifier = Modifier,
    onRefresh: (() -> Unit)? = null,
    refreshEnabled: Boolean = true,
    refreshLoading: Boolean = false,
) {
    val taxiColors = TaxiTheme.colors
    val acceptLabel = stringResource(Res.string.accept)
    val declineLabel = stringResource(Res.string.decline)
    Surface(modifier, shape = MaterialTheme.shapes.large, color = taxiColors.Surface0, shadowElevation = if (TaxiTheme.style == org.example.taximobile.feature.ui.theme.TaxiStyle.Notepad) 0.dp else TaxiSpacing.Xs) {
        Column(Modifier.padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            Text(stringResource(Res.string.ride_offer), style = MaterialTheme.typography.titleMedium)
            Text(pickupSummary, style = MaterialTheme.typography.bodyLarge)
            distanceAndEta?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = taxiColors.Ink700) }
            fare?.let { Text(it, style = MaterialTheme.typography.titleSmall) }
            details.forEach { detail ->
                Text(detail, style = MaterialTheme.typography.bodyMedium, color = taxiColors.Ink700)
            }
            Text(expiryLabel, style = MaterialTheme.typography.bodySmall, color = taxiColors.Ink500)
            expiryFraction?.let { progress ->
                LinearProgressIndicator(
                    progress = { progress.coerceIn(0f, 1f) },
                    color = if (progress < 0.25f) taxiColors.Warning600 else taxiColors.Accent500,
                )
            }
            TaxiButton(
                acceptLabel,
                onAccept,
                modifier = Modifier.heightIn(min = 64.dp).semantics { contentDescription = acceptLabel },
                enabled = acceptEnabled,
                loading = acceptLoading,
            )
            TaxiButton(
                declineLabel,
                onDecline,
                modifier = Modifier.semantics { contentDescription = declineLabel },
                enabled = declineEnabled,
                loading = declineLoading,
                style = TaxiButtonStyle.Secondary,
            )
            onRefresh?.let { refresh ->
                val label = stringResource(Res.string.offer_refresh)
                TaxiButton(label, refresh, modifier = Modifier.semantics { contentDescription = label },
                    enabled = refreshEnabled, loading = refreshLoading, style = TaxiButtonStyle.Secondary)
            }
        }
    }
}
