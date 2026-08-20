package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.status_description

enum class StatusTone { Neutral, Accent, Info, Success, Warning, Danger }

data class StatusToneColors(val foreground: Color, val background: Color)

fun statusToneColors(tone: StatusTone): StatusToneColors = when (tone) {
    StatusTone.Neutral -> StatusToneColors(TaxiColors.Ink700, TaxiColors.Surface2)
    StatusTone.Accent -> StatusToneColors(TaxiColors.Accent600, TaxiColors.Accent100)
    StatusTone.Info -> StatusToneColors(TaxiColors.Info600, TaxiColors.Info100)
    StatusTone.Success -> StatusToneColors(TaxiColors.Success600, TaxiColors.Success100)
    StatusTone.Warning -> StatusToneColors(TaxiColors.Warning600, TaxiColors.Warning100)
    StatusTone.Danger -> StatusToneColors(TaxiColors.Danger600, TaxiColors.Danger100)
}

@Composable
fun StatusPill(label: String, tone: StatusTone, modifier: Modifier = Modifier, showDot: Boolean = true) {
    val colors = statusToneColors(tone)
    val localizedDescription = stringResource(Res.string.status_description, label)
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(TaxiRadii.Pill))
            .background(colors.background)
            .semantics {
                contentDescription = localizedDescription
                liveRegion = LiveRegionMode.Polite
            }
            .padding(horizontal = TaxiSpacing.Sm, vertical = TaxiSpacing.Xs),
        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (showDot) {
            androidx.compose.foundation.layout.Box(
                Modifier.size(8.dp).clip(CircleShape).background(colors.foreground),
            )
        }
        Text(label, color = colors.foreground, style = MaterialTheme.typography.labelMedium)
    }
}
