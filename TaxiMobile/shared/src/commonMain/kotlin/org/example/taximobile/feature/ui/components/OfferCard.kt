package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
fun OfferCard(
    pickupSummary: String,
    distanceAndEta: String?,
    fare: String?,
    expiryLabel: String,
    expiryFraction: Float? = null,
    acceptEnabled: Boolean = true,
    declineEnabled: Boolean = true,
    acceptLoading: Boolean = false,
    declineLoading: Boolean = false,
    onAccept: () -> Unit,
    onDecline: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier, shape = MaterialTheme.shapes.large, color = TaxiColors.Surface0, shadowElevation = TaxiSpacing.Xs) {
        Column(Modifier.padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            Text(stringResource(Res.string.ride_offer), style = MaterialTheme.typography.titleMedium)
            Text(pickupSummary, style = MaterialTheme.typography.bodyLarge)
            distanceAndEta?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = TaxiColors.Ink700) }
            fare?.let { Text(it, style = MaterialTheme.typography.titleSmall) }
            Text(expiryLabel, style = MaterialTheme.typography.bodySmall, color = TaxiColors.Ink500)
            expiryFraction?.let { progress ->
                LinearProgressIndicator(
                    progress = { progress.coerceIn(0f, 1f) },
                    color = if (progress < 0.25f) TaxiColors.Warning600 else TaxiColors.Accent500,
                )
            }
            TaxiButton(
                stringResource(Res.string.accept),
                onAccept,
                enabled = acceptEnabled,
                loading = acceptLoading,
            )
            TaxiButton(
                stringResource(Res.string.decline),
                onDecline,
                enabled = declineEnabled,
                loading = declineLoading,
                style = TaxiButtonStyle.Secondary,
            )
        }
    }
}
