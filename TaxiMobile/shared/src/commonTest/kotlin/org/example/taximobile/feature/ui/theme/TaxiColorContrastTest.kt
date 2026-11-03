package org.example.taximobile.feature.ui.theme

import androidx.compose.ui.graphics.Color
import kotlin.math.pow
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class TaxiColorContrastTest {
    private fun linear(channel: Float): Double {
        val value = channel.toDouble()
        return if (value <= 0.04045) value / 12.92 else ((value + 0.055) / 1.055).pow(2.4)
    }

    private fun luminance(color: Color): Double =
        0.2126 * linear(color.red) + 0.7152 * linear(color.green) + 0.0722 * linear(color.blue)

    private fun contrast(first: Color, second: Color): Double {
        val a = luminance(first)
        val b = luminance(second)
        return (maxOf(a, b) + 0.05) / (minOf(a, b) + 0.05)
    }

    @Test
    fun default_controls_and_primary_actions_use_the_selected_folded_style() {
        val scheme = taxiLightColorScheme()
        assertEquals(TaxiColors.Accent500, scheme.primary)
        assertTrue(contrast(scheme.primary, TaxiColors.Surface0) >= 4.5)
        assertTrue(contrast(TaxiColors.Accent500, Color.White) >= 4.5)
        assertTrue(contrast(TaxiColors.Accent500, TaxiColors.Surface0) >= 4.5)
    }

    @Test
    fun notepad_material_dialogs_and_elevated_surfaces_stay_grayscale_and_readable() {
        val scheme = taxiLightColorScheme(taxiPalette(TaxiStyle.Notepad))
        val surfaces = listOf(
            scheme.surface, scheme.surfaceVariant, scheme.surfaceDim, scheme.surfaceBright,
            scheme.surfaceContainerLowest, scheme.surfaceContainerLow, scheme.surfaceContainer,
            scheme.surfaceContainerHigh, scheme.surfaceContainerHighest,
        )
        for (color in surfaces + listOf(scheme.surfaceTint, scheme.inverseSurface,
                scheme.inverseOnSurface, scheme.inversePrimary)) {
            assertEquals(color.red, color.green, "Notepad must not inherit a colored Material role")
            assertEquals(color.green, color.blue, "Notepad must not inherit a colored Material role")
        }
        for (surface in surfaces) {
            assertTrue(contrast(scheme.onSurface, surface) >= 4.5,
                "Notepad text must remain readable on dialog and container surfaces")
        }
        assertTrue(contrast(scheme.inverseOnSurface, scheme.inverseSurface) >= 4.5)
    }

    @Test
    fun confirmation_action_roles_are_readable_in_every_selected_style() {
        for (style in TaxiStyle.entries) {
            val palette = taxiPalette(style)
            val scheme = taxiLightColorScheme(palette)
            assertTrue(contrast(scheme.onPrimary, palette.Accent500) >= 4.5,
                "$style confirmation text must be readable on its primary action")
            assertTrue(contrast(scheme.onError, palette.Danger600) >= 4.5,
                "$style destructive confirmation text must be readable")
        }
    }
}
