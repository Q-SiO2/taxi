package org.example.taximobile.feature.ui.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.MotionDurationScale
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.layout.boundsInWindow
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.currentCoroutineContext
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.example.taximobile.feature.ui.theme.TaxiTheme
import kotlin.math.sin

fun taxiDecorativeMotionAllowed(style: TaxiStyle, motionScale: Float, resumed: Boolean): Boolean =
    style.decorativeMotion && motionScale > 0f && resumed

/** Original abstract geometry; no city, vehicle, map route or fabricated trip fact. */
@Composable
fun TaxiEntryFrame(modifier: Modifier = Modifier) {
    val style = TaxiTheme.style
    val colors = TaxiTheme.colors
    val rtl = LocalLayoutDirection.current == LayoutDirection.Rtl
    val lifecycle by LocalLifecycleOwner.current.lifecycle.currentStateFlow.collectAsState()
    var visible by remember { mutableStateOf(false) }
    val progress = remember { Animatable(1f) }
    LaunchedEffect(style, lifecycle, visible) {
        val scale = currentCoroutineContext()[MotionDurationScale]?.scaleFactor ?: 1f
        if (visible && taxiDecorativeMotionAllowed(style, scale, lifecycle.isAtLeast(Lifecycle.State.RESUMED))) {
            progress.snapTo(0f)
            progress.animateTo(1f, tween(2400))
        } else {
            progress.snapTo(1f)
        }
    }
    Canvas(modifier.fillMaxWidth().height(if (style == TaxiStyle.Notepad) 28.dp else 116.dp)
        .testTag("identity-frame-${style.storageValue}")
        .onGloballyPositioned { visible = !it.boundsInWindow().isEmpty }) {
        val w = size.width
        val h = size.height
        val drift = sin(progress.value * kotlin.math.PI.toFloat()) * w * 0.07f
        val cobalt = Color(0xFF4658F0)
        val pink = Color(0xFFFF78B4)
        val orange = Color(0xFFFF8C4C)
        val mint = Color(0xFFB6E9C7)
        when (style) {
            TaxiStyle.FoldedStreets -> {
                drawRect(Brush.linearGradient(listOf(cobalt, pink, orange, mint), start = Offset(drift, 0f), end = Offset(w + drift, h)))
                drawPath(Path().apply {
                    moveTo(0f, h * 0.75f); lineTo(w * 0.35f, h * 0.15f)
                    lineTo(w * 0.6f, h); lineTo(0f, h); close()
                }, colors.surface)
                drawPath(Path().apply {
                    moveTo(w * 0.6f, 0f); lineTo(w * 0.78f, h * 0.5f)
                    lineTo(w, h * 0.15f); lineTo(w, 0f); close()
                }, Color(0xFFFFDC65))
                drawLine(colors.ink, Offset(w * 0.35f, h * 0.15f), Offset(w * 0.6f, h), 2.dp.toPx())
            }
            TaxiStyle.StreetPress -> {
                drawRect(Color(0xFFFFDD59))
                drawRect(pink, Offset(w * 0.06f + drift, h * 0.15f), Size(w * 0.42f, h * 0.7f))
                drawPath(Path().apply {
                    moveTo(w * 0.42f, h); lineTo(w * 0.68f, 0f)
                    lineTo(w * 0.88f, 0f); lineTo(w * 0.72f, h); close()
                }, cobalt)
                drawRect(mint, Offset(w * 0.78f - drift, h * 0.22f), Size(w * 0.23f, h * 0.6f))
                drawLine(colors.ink, Offset(0f, h - 2.dp.toPx()), Offset(w, h - 2.dp.toPx()), 4.dp.toPx())
                repeat(4) { index ->
                    drawLine(colors.ink, Offset(w * 0.1f, h * (0.3f + index * 0.13f)), Offset(w * 0.3f, h * (0.3f + index * 0.13f)), 2.dp.toPx())
                }
            }
            TaxiStyle.GlazedMachine -> {
                drawRoundRect(colors.ink, Offset(4.dp.toPx(), 5.dp.toPx()), Size(w - 4.dp.toPx(), h - 5.dp.toPx()), CornerRadius(28.dp.toPx()))
                drawRoundRect(Brush.linearGradient(listOf(mint, pink, orange), start = Offset(drift, h), end = Offset(w, 0f)), size = Size(w - 5.dp.toPx(), h - 6.dp.toPx()), cornerRadius = CornerRadius(28.dp.toPx()))
                drawCircle(Color.White.copy(alpha = 0.35f), h * 0.7f, Offset(w * 0.78f - drift, h * 0.25f))
                repeat(180) { index ->
                    val x = ((index * 73) % 997) / 997f * w
                    val y = ((index * 157) % 991) / 991f * h
                    drawCircle(colors.ink.copy(alpha = 0.08f), 0.7.dp.toPx(), Offset(x, y))
                }
            }
            TaxiStyle.Notepad -> {
                drawLine(colors.stroke.copy(alpha = 0.45f), Offset(0f, h * 0.4f), Offset(w, h * 0.4f), 1.dp.toPx())
                drawLine(colors.stroke.copy(alpha = 0.45f), Offset(0f, h * 0.9f), Offset(w, h * 0.9f), 1.dp.toPx())
                val margin = if (rtl) w - 18.dp.toPx() else 18.dp.toPx()
                drawLine(colors.stroke, Offset(margin, 0f), Offset(margin, h), 1.dp.toPx())
            }
        }
    }
}
