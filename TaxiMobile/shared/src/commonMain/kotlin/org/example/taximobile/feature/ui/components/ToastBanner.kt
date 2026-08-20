package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.theme.TaxiMotion
import kotlinx.coroutines.delay

@Composable
fun ToastBanner(
    message: String,
    tone: StatusTone = StatusTone.Info,
    modifier: Modifier = Modifier,
    onDismiss: (() -> Unit)? = null,
) {
    LaunchedEffect(message, tone, onDismiss) {
        if (onDismiss != null && tone != StatusTone.Danger) {
            delay(TaxiMotion.InformationalBannerMillis.toLong())
            onDismiss()
        }
    }
    val colors = statusToneColors(tone)
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(colors.background, RoundedCornerShape(TaxiRadii.Md))
            .semantics(mergeDescendants = true) {
                liveRegion = if (tone == StatusTone.Danger) LiveRegionMode.Assertive else LiveRegionMode.Polite
            }
            .padding(TaxiSpacing.Md),
    ) {
        Text(message, color = colors.foreground, style = MaterialTheme.typography.bodyMedium)
    }
}
