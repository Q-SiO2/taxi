package org.example.taximobile.feature.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing

/** Backend-confirmed success: a 320 ms check draw followed by a static row. */
@Composable
fun SuccessConfirmation(label: String, eventSequence: Long, modifier: Modifier = Modifier) {
    var started by remember(eventSequence) { mutableStateOf(false) }
    LaunchedEffect(eventSequence) { started = true }
    val progress by animateFloatAsState(
        targetValue = if (started) 1f else 0f,
        animationSpec = tween(durationMillis = 320),
        label = "confirmed-action-check",
    )
    Surface(
        modifier = modifier.semantics { liveRegion = LiveRegionMode.Polite },
        color = TaxiColors.Success100,
        shape = MaterialTheme.shapes.medium,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Sm),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Canvas(Modifier.size(24.dp)) {
                val first = Offset(size.width * 0.18f, size.height * 0.52f)
                val middle = Offset(size.width * 0.43f, size.height * 0.76f)
                val last = Offset(size.width * 0.84f, size.height * 0.26f)
                val firstLength = (middle - first).getDistance()
                val secondLength = (last - middle).getDistance()
                val distance = progress * (firstLength + secondLength)
                val firstFraction = (distance / firstLength).coerceIn(0f, 1f)
                drawLine(
                    color = TaxiColors.Success600,
                    start = first,
                    end = first + (middle - first) * firstFraction,
                    strokeWidth = 3.dp.toPx(),
                    cap = StrokeCap.Round,
                )
                if (distance > firstLength) {
                    val secondFraction = ((distance - firstLength) / secondLength).coerceIn(0f, 1f)
                    drawLine(
                        color = TaxiColors.Success600,
                        start = middle,
                        end = middle + (last - middle) * secondFraction,
                        strokeWidth = 3.dp.toPx(),
                        cap = StrokeCap.Round,
                    )
                }
            }
            Text(label, color = TaxiColors.Success600, style = MaterialTheme.typography.labelLarge)
        }
    }
}
