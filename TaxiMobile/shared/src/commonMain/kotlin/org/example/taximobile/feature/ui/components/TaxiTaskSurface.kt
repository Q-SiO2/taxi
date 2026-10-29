package org.example.taximobile.feature.ui.components

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.example.taximobile.feature.ui.theme.TaxiTheme

/**
 * Compact material grammar for functional surfaces. Paint only: no layout,
 * semantics, input, animation controller or domain state. Controls keep their
 * opaque surfaces; registration marks stay inside the existing content gutter.
 */
@Composable
fun taxiTaskSurface(modifier: Modifier = Modifier): Modifier {
    val style = TaxiTheme.style
    val colors = TaxiTheme.colors
    val rtl = LocalLayoutDirection.current == LayoutDirection.Rtl
    return modifier.drawWithCache {
        val unit = 1.dp.toPx()
        val gutter = 12.dp.toPx()
        val edge = 6.dp.toPx()
        val leading = if (rtl) size.width - edge - 2 * unit else 2 * unit
        val rail = if (rtl) size.width - gutter else gutter
        val trailing = if (rtl) unit else size.width - 3 * unit
        val innerTrailing = if (rtl) trailing + 3 * unit else trailing - 3 * unit
        val cobalt = Color(0xFF4658F0)
        val pink = Color(0xFFFF78B4)
        val orange = Color(0xFFFF8C4C)
        val mint = Color(0xFFB6E9C7)
        val spectral = Brush.verticalGradient(listOf(cobalt, pink, orange, mint))
        val glaze = Brush.verticalGradient(listOf(mint, pink, Color(0xFFF7F0E5)))
        val fold = Path().apply {
            val x = if (rtl) size.width else 0f
            val sign = if (rtl) -1f else 1f
            moveTo(x, 28 * unit)
            lineTo(x + sign * 10 * unit, 40 * unit)
            lineTo(x, 52 * unit)
            close()
        }
        onDrawWithContent {
            // Paper rules sit behind ink and opaque controls. They are static
            // structure, not a texture or an ornamental performance.
            if (style == TaxiStyle.Notepad) {
                var y = 48 * unit
                while (y < size.height) {
                    drawLine(colors.stroke.copy(alpha = 0.14f), Offset(0f, y), Offset(size.width, y), unit * 0.5f)
                    y += 28 * unit
                }
            }
            drawContent()
            when (style) {
                TaxiStyle.FoldedStreets -> {
                    drawRect(spectral, Offset(leading, 0f), Size(edge, size.height))
                    drawPath(fold, Color(0xFFFFDC65))
                    drawLine(colors.ink.copy(alpha = 0.55f), Offset(rail, 0f), Offset(rail, 24 * unit), unit)
                    drawLine(mint, Offset(trailing, 0f), Offset(trailing, size.height), unit)
                }
                TaxiStyle.StreetPress -> {
                    drawLine(colors.ink, Offset(0f, unit), Offset(size.width, unit), 2 * unit)
                    drawLine(colors.ink.copy(alpha = 0.65f), Offset(rail, 0f), Offset(rail, size.height), unit)
                    listOf(pink, cobalt, mint).forEachIndexed { index, color ->
                        drawRect(color, Offset(leading, (24 + index * 32) * unit), Size(edge, 22 * unit))
                    }
                }
                TaxiStyle.GlazedMachine -> {
                    drawRoundRect(glaze, Offset(leading, 4 * unit), Size(edge, (size.height - 8 * unit).coerceAtLeast(0f)), CornerRadius(3 * unit))
                    drawLine(colors.ink.copy(alpha = 0.18f), Offset(trailing, 7 * unit), Offset(trailing, size.height), 2 * unit)
                    drawLine(colors.ink.copy(alpha = 0.06f), Offset(innerTrailing, 10 * unit), Offset(innerTrailing, size.height), unit)
                    repeat(48) { index ->
                        val x = if (rtl) size.width - ((index * 7) % 10 + 1) * unit else ((index * 7) % 10 + 1) * unit
                        val y = ((index * 37) % 997) / 997f * size.height
                        drawCircle(colors.ink.copy(alpha = 0.12f), unit * 0.35f, Offset(x, y))
                    }
                }
                TaxiStyle.Notepad -> {
                    drawLine(colors.stroke.copy(alpha = 0.45f), Offset(rail, 0f), Offset(rail, size.height), unit)
                }
            }
        }
    }
}
