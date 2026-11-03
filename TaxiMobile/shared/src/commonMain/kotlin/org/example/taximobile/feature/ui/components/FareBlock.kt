package org.example.taximobile.feature.ui.components

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

data class FareBreakdownRow(val label: String, val amount: String)

@Composable
fun FareBlock(
    amount: String,
    currency: String,
    pricingRuleVersion: String?,
    finalFare: Boolean,
    modifier: Modifier = Modifier,
    breakdown: List<FareBreakdownRow> = emptyList(),
) {
    val taxiColors = TaxiTheme.colors
    Column(modifier, verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
        Text(
            stringResource(if (finalFare) Res.string.final_fare else Res.string.estimated_fare),
            style = MaterialTheme.typography.labelMedium,
            color = taxiColors.Ink500,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
            Text(amount, style = MaterialTheme.typography.displaySmall, color = taxiColors.Ink900)
            Text(currency, style = MaterialTheme.typography.bodySmall, color = taxiColors.Ink500)
        }
        // The version is retained in the backend quote/receipt, but is not
        // useful in the primary fare hierarchy of a passenger or driver screen.
        breakdown.forEach { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(row.label, style = MaterialTheme.typography.bodyMedium)
                Text(row.amount, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
