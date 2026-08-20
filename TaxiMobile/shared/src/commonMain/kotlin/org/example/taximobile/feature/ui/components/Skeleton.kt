package org.example.taximobile.feature.ui.components

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiMotion

@Composable
fun Skeleton(modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "Taxi skeleton")
    val alpha by transition.animateFloat(
        initialValue = 0.55f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(TaxiMotion.EmphasizedMillis * 3), RepeatMode.Reverse),
        label = "Taxi skeleton alpha",
    )
    androidx.compose.foundation.layout.Box(
        modifier.height(20.dp).alpha(alpha).background(TaxiColors.Navy100, RoundedCornerShape(TaxiRadii.Sm)),
    )
}
