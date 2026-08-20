package org.example.taximobile.feature.ui

import androidx.compose.ui.graphics.Color
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.components.TaxiSheetSnap
import org.example.taximobile.feature.ui.components.accessibleTaxiSheetSnap
import org.example.taximobile.feature.ui.components.statusToneColors
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing

class TaxiDesignTokensTest {
    @Test
    fun palette_matches_the_approved_ui_contract() {
        assertEquals(Color(0xFF071426), TaxiColors.Navy950)
        assertEquals(Color(0xFF0B1F3A), TaxiColors.Navy900)
        assertEquals(Color(0xFFD6A800), TaxiColors.Accent500)
        assertEquals(Color(0xFF14804A), TaxiColors.Success600)
        assertEquals(Color(0xFFB7791F), TaxiColors.Warning600)
        assertEquals(Color(0xFFC53030), TaxiColors.Danger600)
        assertEquals(Color(0xFFF6F8FB), TaxiColors.Surface1)
    }

    @Test
    fun primary_button_pair_exceeds_wcag_aa_normal_text_contrast() {
        assertTrue(contrastRatio(TaxiColors.Navy950, TaxiColors.Accent500) >= 4.5)
    }

    @Test
    fun spacing_and_radius_scales_keep_the_documented_values() {
        assertEquals(listOf(4f, 8f, 12f, 16f, 20f, 24f, 32f, 40f, 48f, 64f), listOf(
            TaxiSpacing.Xxs.value,
            TaxiSpacing.Xs.value,
            TaxiSpacing.Sm.value,
            TaxiSpacing.Md.value,
            TaxiSpacing.Lg.value,
            TaxiSpacing.Xl.value,
            TaxiSpacing.Xxl.value,
            TaxiSpacing.Xxxl.value,
            TaxiSpacing.Xxxxl.value,
            TaxiSpacing.Huge.value,
        ))
        assertEquals(listOf(8f, 12f, 16f, 24f, 999f), listOf(
            TaxiRadii.Sm.value,
            TaxiRadii.Md.value,
            TaxiRadii.Lg.value,
            TaxiRadii.Xl.value,
            TaxiRadii.Pill.value,
        ))
    }

    @Test
    fun status_tones_keep_distinct_explicit_semantics() {
        assertEquals(TaxiColors.Success600, statusToneColors(StatusTone.Success).foreground)
        assertEquals(TaxiColors.Warning600, statusToneColors(StatusTone.Warning).foreground)
        assertEquals(TaxiColors.Danger600, statusToneColors(StatusTone.Danger).foreground)
        assertEquals(TaxiColors.Info600, statusToneColors(StatusTone.Info).foreground)
    }

    @Test
    fun shared_component_contract_exposes_all_button_and_sheet_states() {
        assertEquals(
            listOf("Primary", "Secondary", "Tertiary", "Destructive", "ToneLike"),
            TaxiButtonStyle.entries.map { it.name },
        )
        assertEquals(
            listOf(0.28f, 0.48f, 0.78f),
            TaxiSheetSnap.entries.map { it.heightFraction },
        )
    }

    @Test
    fun large_text_promotes_compact_sheet_states_without_collapsing_explicit_expansion() {
        assertEquals(TaxiSheetSnap.Peek, accessibleTaxiSheetSnap(TaxiSheetSnap.Peek, 1.0f))
        assertEquals(TaxiSheetSnap.Half, accessibleTaxiSheetSnap(TaxiSheetSnap.Peek, 1.3f))
        assertEquals(TaxiSheetSnap.Half, accessibleTaxiSheetSnap(TaxiSheetSnap.Half, 1.5f))
        assertEquals(TaxiSheetSnap.Expanded, accessibleTaxiSheetSnap(TaxiSheetSnap.Peek, 1.6f))
        assertEquals(TaxiSheetSnap.Expanded, accessibleTaxiSheetSnap(TaxiSheetSnap.Half, 2.0f))
        assertEquals(TaxiSheetSnap.Expanded, accessibleTaxiSheetSnap(TaxiSheetSnap.Expanded, 1.0f))
    }
}

private fun contrastRatio(first: Color, second: Color): Double {
    val firstLuminance = relativeLuminance(first)
    val secondLuminance = relativeLuminance(second)
    return (max(firstLuminance, secondLuminance) + 0.05) / (min(firstLuminance, secondLuminance) + 0.05)
}

private fun relativeLuminance(color: Color): Double =
    0.2126 * linearize(color.red.toDouble()) +
        0.7152 * linearize(color.green.toDouble()) +
        0.0722 * linearize(color.blue.toDouble())

private fun linearize(channel: Double): Double =
    if (channel <= 0.04045) channel / 12.92 else ((channel + 0.055) / 1.055).pow(2.4)
