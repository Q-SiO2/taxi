package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.theme.TaxiTheme
import org.example.taximobile.feature.ui.text.ltrIsolate

/** Passenger-safe driver summary. It deliberately accepts no contact or earnings fields. */
@Composable
fun DriverCard(
    displayName: String,
    vehicleDescription: String,
    taxiIdentifier: String?,
    statusLabel: String,
    statusTone: StatusTone,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier, shape = MaterialTheme.shapes.large, color = TaxiColors.Surface0, tonalElevation = TaxiSpacing.Xxs) {
        Column(Modifier.padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
            Text(displayName, style = MaterialTheme.typography.titleMedium)
            StatusPill(statusLabel, statusTone)
            Text(vehicleDescription, style = MaterialTheme.typography.bodyMedium, color = TaxiColors.Ink700)
            taxiIdentifier?.let {
                Text(ltrIsolate(it), style = TaxiTheme.typography.monoMedium, color = TaxiColors.Ink900)
            }
        }
    }
}
