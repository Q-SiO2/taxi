package org.example.taximobile.feature.ui.components

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiMotion
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing

enum class TaxiSheetSnap(val heightFraction: Float) { Peek(0.28f), Half(0.48f), Expanded(0.78f) }

/**
 * Promotes compact sheet states when system text scaling would otherwise hide
 * the title and primary action in a short viewport. Content remains scrollable,
 * but users should not have to discover a gesture before reaching the first
 * actionable control.
 */
fun accessibleTaxiSheetSnap(requested: TaxiSheetSnap, fontScale: Float): TaxiSheetSnap {
    val minimum = when {
        fontScale >= 1.6f -> TaxiSheetSnap.Expanded
        fontScale >= 1.3f -> TaxiSheetSnap.Half
        else -> TaxiSheetSnap.Peek
    }
    return TaxiSheetSnap.entries[maxOf(requested.ordinal, minimum.ordinal)]
}

@Composable
fun TaxiSheet(
    snap: TaxiSheetSnap,
    onSnapChange: (TaxiSheetSnap) -> Unit,
    modifier: Modifier = Modifier,
    modal: Boolean = false,
    content: @Composable () -> Unit,
) {
    val effectiveSnap = accessibleTaxiSheetSnap(snap, LocalDensity.current.fontScale)
    BoxWithConstraints(modifier.fillMaxSize()) {
        if (modal && effectiveSnap == TaxiSheetSnap.Expanded) {
            Box(Modifier.fillMaxSize().background(TaxiColors.Scrim))
        }
        val targetHeight = maxHeight * effectiveSnap.heightFraction
        val animatedHeight by animateDpAsState(
            targetValue = targetHeight,
            animationSpec = androidx.compose.animation.core.tween(TaxiMotion.StandardMillis, easing = TaxiMotion.StandardEasing),
            label = "Taxi sheet height",
        )
        var accumulatedDrag by remember { mutableFloatStateOf(0f) }
        Surface(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .height(animatedHeight)
                .testTag("taxi-sheet")
                .pointerInput(effectiveSnap) {
                    detectVerticalDragGestures(
                        onDragStart = { accumulatedDrag = 0f },
                        onVerticalDrag = { _, amount -> accumulatedDrag += amount },
                        onDragEnd = {
                            val ordered = TaxiSheetSnap.entries
                            val current = ordered.indexOf(effectiveSnap)
                            val dragThreshold = 40.dp.toPx()
                            val next = when {
                                accumulatedDrag < -dragThreshold -> (current + 1).coerceAtMost(ordered.lastIndex)
                                accumulatedDrag > dragThreshold -> (current - 1).coerceAtLeast(0)
                                else -> current
                            }
                            onSnapChange(ordered[next])
                        },
                    )
                },
            shape = RoundedCornerShape(topStart = TaxiRadii.Xl, topEnd = TaxiRadii.Xl),
            color = TaxiColors.Surface0,
            shadowElevation = 12.dp,
        ) {
            Column(
                Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = TaxiSpacing.Xl, vertical = TaxiSpacing.Sm),
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                Box(
                    Modifier.align(Alignment.CenterHorizontally).width(32.dp).height(4.dp)
                        .background(TaxiColors.Ink300, RoundedCornerShape(TaxiRadii.Pill)),
                )
                content()
            }
        }
    }
}
