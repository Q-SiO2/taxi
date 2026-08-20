package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii

@Composable
fun TaxiSegmentedControl(
    firstLabel: String,
    secondLabel: String,
    firstSelected: Boolean,
    onFirstSelected: () -> Unit,
    onSecondSelected: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier.fillMaxWidth().clip(RoundedCornerShape(TaxiRadii.Md)).background(TaxiColors.Surface2).padding(4.dp),
    ) {
        Segment(firstLabel, firstSelected, onFirstSelected, Modifier.weight(1f))
        Segment(secondLabel, !firstSelected, onSecondSelected, Modifier.weight(1f))
    }
}

@Composable
private fun Segment(label: String, selected: Boolean, onClick: () -> Unit, modifier: Modifier) {
    TextButton(
        onClick = onClick,
        modifier = modifier.clip(RoundedCornerShape(TaxiRadii.Sm)).background(if (selected) TaxiColors.Surface0 else Color.Transparent),
    ) {
        Text(
            label,
            color = if (selected) TaxiColors.Ink900 else TaxiColors.Ink500,
            style = MaterialTheme.typography.labelLarge,
        )
    }
}
