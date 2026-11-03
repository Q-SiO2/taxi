package org.example.taximobile.feature.ui.components

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.Dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiMotion
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.sheet_expand
import taximobile.shared.generated.resources.sheet_collapse
import kotlin.math.abs

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

/** Leave room for the toolbar, safe top area and two map shortcut targets. */
fun taxiSheetAllowsMapActions(requested: TaxiSheetSnap, fontScale: Float, viewportHeight: Dp): Boolean =
    viewportHeight * (1f - accessibleTaxiSheetSnap(requested, fontScale).heightFraction) >= 240.dp

@Composable
fun TaxiSheet(
    snap: TaxiSheetSnap,
    onSnapChange: (TaxiSheetSnap) -> Unit,
    modifier: Modifier = Modifier,
    modal: Boolean = false,
    safeInsets: WindowInsets = WindowInsets.safeDrawing,
    keyboardInsets: WindowInsets = WindowInsets.ime,
    content: @Composable () -> Unit,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    val effectiveSnap = accessibleTaxiSheetSnap(snap, LocalDensity.current.fontScale)
    val minimumSnap = accessibleTaxiSheetSnap(TaxiSheetSnap.Peek, LocalDensity.current.fontScale)
    val scrollState = rememberScrollState()
    val currentOnSnapChange by rememberUpdatedState(onSnapChange)
    val expandLabel = stringResource(Res.string.sheet_expand)
    val collapseLabel = stringResource(Res.string.sheet_collapse)
    // IME space belongs to the sheet's outer layout, before snap sizing. If it
    // is subtracted inside a peek sheet, an ordinary keyboard can consume the
    // entire scroll viewport and remove the focused field from accessibility.
    // This overlay consumes its own insets; the separate map stays edge-to-edge.
    BoxWithConstraints(
        modifier.fillMaxSize().windowInsetsPadding(keyboardInsets.only(WindowInsetsSides.Bottom)),
    ) {
        if (modal && effectiveSnap == TaxiSheetSnap.Expanded) {
            Box(Modifier.fillMaxSize().background(taxiColors.Scrim))
        }
        val targetHeight = maxHeight * effectiveSnap.heightFraction
        val animatedHeight by animateDpAsState(
            targetValue = targetHeight,
            animationSpec = androidx.compose.animation.core.tween(TaxiMotion.StandardMillis, easing = TaxiMotion.StandardEasing),
            label = "Taxi sheet height",
        )
        Surface(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .height(animatedHeight)
                .testTag("taxi-sheet")
                .semantics {
                    customActions = buildList {
                        if (effectiveSnap != TaxiSheetSnap.Expanded) {
                            add(CustomAccessibilityAction(expandLabel) {
                                currentOnSnapChange(TaxiSheetSnap.entries[effectiveSnap.ordinal + 1])
                                true
                            })
                        }
                        if (effectiveSnap.ordinal > minimumSnap.ordinal) {
                            add(CustomAccessibilityAction(collapseLabel) {
                                currentOnSnapChange(TaxiSheetSnap.entries[effectiveSnap.ordinal - 1])
                                true
                            })
                        }
                    }
                }
                .pointerInput(effectiveSnap, minimumSnap) {
                    awaitEachGesture {
                        val down = awaitFirstDown(requireUnconsumed = false, pass = PointerEventPass.Initial)
                        // Own only the visible grabber's 48dp drag area. Initial
                        // pass lets it claim a drag before the child scrollable;
                        // taps and gestures started in the body remain with it.
                        if (down.position.y + scrollState.value > 48.dp.toPx()) return@awaitEachGesture
                        var vertical = 0f
                        var horizontal = 0f
                        var dragging = false
                        while (true) {
                            val event = awaitPointerEvent(PointerEventPass.Initial)
                            val change = event.changes.firstOrNull { it.id == down.id } ?: break
                            if (change.isConsumed || event.changes.count { it.pressed } > 1) break
                            vertical += change.position.y - change.previousPosition.y
                            horizontal += change.position.x - change.previousPosition.x
                            if (!dragging && abs(horizontal) > viewConfiguration.touchSlop &&
                                abs(horizontal) > abs(vertical)) break
                            if (abs(vertical) > viewConfiguration.touchSlop) dragging = true
                            if (dragging) change.consume()
                            if (!change.pressed) {
                                val next = when {
                                    vertical < -40.dp.toPx() -> effectiveSnap.ordinal + 1
                                    vertical > 40.dp.toPx() -> effectiveSnap.ordinal - 1
                                    else -> effectiveSnap.ordinal
                                }.coerceIn(minimumSnap.ordinal, TaxiSheetSnap.entries.lastIndex)
                                if (dragging && next != effectiveSnap.ordinal) {
                                    currentOnSnapChange(TaxiSheetSnap.entries[next])
                                }
                                break
                            }
                        }
                    }
                },
            shape = RoundedCornerShape(topStart = taxiRadii.Xl, topEnd = taxiRadii.Xl),
            color = taxiColors.Surface0,
            shadowElevation = if (TaxiTheme.style == org.example.taximobile.feature.ui.theme.TaxiStyle.Notepad) 0.dp else 12.dp,
        ) {
            Column(
                taxiTaskSurface(Modifier.fillMaxSize()
                    .windowInsetsPadding(safeInsets.only(WindowInsetsSides.Bottom + WindowInsetsSides.Horizontal))
                    .testTag("taxi-sheet-scroll-content"))
                    .verticalScroll(scrollState)
                    .padding(horizontal = TaxiSpacing.Xl, vertical = TaxiSpacing.Sm),
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                Box(
                    Modifier.align(Alignment.CenterHorizontally).width(32.dp).height(4.dp)
                        .background(taxiColors.Ink300, RoundedCornerShape(taxiRadii.Pill)),
                )
                content()
            }
        }
    }
}
