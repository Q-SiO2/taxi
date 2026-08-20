package org.example.taximobile.feature.ui.components

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
import org.example.taximobile.feature.ui.text.ltrIsolate
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
    Column(modifier, verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
        Text(
            stringResource(if (finalFare) Res.string.final_fare else Res.string.estimated_fare),
            style = MaterialTheme.typography.labelMedium,
            color = TaxiColors.Ink500,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
            Text(amount, style = MaterialTheme.typography.displaySmall, color = TaxiColors.Ink900)
            Text(currency, style = MaterialTheme.typography.bodySmall, color = TaxiColors.Ink500)
        }
        pricingRuleVersion?.let {
            Text(
                stringResource(Res.string.tariff_value, ltrIsolate(it)),
                style = MaterialTheme.typography.bodySmall,
                color = TaxiColors.Ink500,
            )
        }
        breakdown.forEach { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(row.label, style = MaterialTheme.typography.bodyMedium)
                Text(row.amount, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
