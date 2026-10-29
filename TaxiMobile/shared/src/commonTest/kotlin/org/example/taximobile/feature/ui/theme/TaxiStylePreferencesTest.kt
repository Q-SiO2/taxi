package org.example.taximobile.feature.ui.theme

import androidx.compose.ui.graphics.Color
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.ui.components.statusToneColors
import org.example.taximobile.feature.ui.components.taxiDecorativeMotionAllowed
import kotlin.math.pow
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class TaxiStylePreferencesTest {
    private class Store(var value: String? = null, var fail: Boolean = false) : TaxiStyleStore {
        override fun read(): String? { check(!fail); return value }
        override fun write(value: String) { check(!fail); this.value = value }
    }

    @Test
    fun all_four_stable_values_round_trip_and_unknown_values_fall_back() {
        val store = Store()
        TaxiStyle.entries.forEach { style ->
            TaxiStylePreferences(store).select(style)
            assertEquals(style.storageValue, store.value)
            assertEquals(style, TaxiStylePreferences(store).style)
        }
        assertEquals(TaxiStyle.FoldedStreets, TaxiStyle.fromStorage("gold"))
        assertEquals(TaxiStyle.FoldedStreets, TaxiStyle.fromStorage(null))
        assertEquals(listOf("folded_streets", "street_press", "glazed_machine", "notepad"), TaxiStyle.entries.map { it.storageValue })
    }

    @Test
    fun failed_storage_keeps_a_usable_selection_and_exposes_retry_state() {
        val store = Store(fail = true)
        val preferences = TaxiStylePreferences(store)
        assertTrue(preferences.storageFailed)
        preferences.select(TaxiStyle.Notepad)
        assertEquals(TaxiStyle.Notepad, preferences.style)
        assertTrue(preferences.storageFailed)
        store.fail = false
        preferences.select(TaxiStyle.Notepad)
        assertFalse(preferences.storageFailed)
        assertEquals(TaxiStyle.Notepad, TaxiStylePreferences(store).style)
    }

    @Test
    fun every_style_has_readable_task_text_action_labels_and_control_edges() {
        TaxiStyle.entries.forEach { style ->
            val colors = taxiPalette(style)
            assertTrue(contrast(colors.ink, colors.surface) >= 4.5, "$style body")
            assertTrue(contrast(colors.secondaryInk, colors.surface) >= 4.5, "$style supporting text")
            assertTrue(contrast(Color.White, colors.action) >= 4.5, "$style action")
            assertTrue(contrast(colors.stroke, colors.surface) >= 3.0, "$style outline")
            StatusTone.entries.forEach { tone ->
                val status = statusToneColors(tone, colors)
                assertTrue(contrast(status.foreground, status.background) >= 4.5, "$style $tone")
            }
        }
    }

    @Test
    fun notepad_keeps_gray_semantics_square_edges_and_no_decorative_motion() {
        val colors = taxiPalette(TaxiStyle.Notepad)
        val tokens = listOf(colors.page, colors.surface, colors.ink, colors.secondaryInk, colors.action,
            colors.selection, colors.stroke, colors.Success600, colors.Success100, colors.Warning600,
            colors.Warning100, colors.Danger600, colors.Danger100, colors.Info600, colors.Info100)
        tokens.forEach { assertEquals(it.red, it.green); assertEquals(it.green, it.blue) }
        assertEquals(0f, TaxiStyle.Notepad.cornerRadii().Lg.value)
        assertFalse(taxiDecorativeMotionAllowed(TaxiStyle.Notepad, 1f, true))
        assertFalse(taxiDecorativeMotionAllowed(TaxiStyle.FoldedStreets, 0f, true))
        assertFalse(taxiDecorativeMotionAllowed(TaxiStyle.StreetPress, 1f, false))
        assertTrue(taxiDecorativeMotionAllowed(TaxiStyle.GlazedMachine, 1f, true))
    }

    private fun luminance(color: Color): Double {
        fun linear(channel: Float): Double = if (channel <= 0.04045f) channel / 12.92 else ((channel + 0.055) / 1.055).pow(2.4)
        return 0.2126 * linear(color.red) + 0.7152 * linear(color.green) + 0.0722 * linear(color.blue)
    }
    private fun contrast(a: Color, b: Color): Double =
        (maxOf(luminance(a), luminance(b)) + 0.05) / (minOf(luminance(a), luminance(b)) + 0.05)
}
