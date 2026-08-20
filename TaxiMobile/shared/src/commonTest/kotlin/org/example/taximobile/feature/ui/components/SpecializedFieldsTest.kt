package org.example.taximobile.feature.ui.components

import kotlin.test.Test
import kotlin.test.assertEquals

class SpecializedFieldsTest {
    @Test
    fun moroccan_phone_input_normalizes_supported_paste_shapes() {
        val expected = "+212612345678"
        assertEquals(expected, normalizeMoroccanPhoneInput("0612345678"))
        assertEquals(expected, normalizeMoroccanPhoneInput("+212 6 12 34 56 78"))
        assertEquals(expected, normalizeMoroccanPhoneInput("212612345678"))
        assertEquals(expected, normalizeMoroccanPhoneInput("00212 612-345-678"))
    }

    @Test
    fun moroccan_phone_display_is_readable_without_changing_canonical_value() {
        assertEquals("+212 | 6 12 34 56 78", formatMoroccanPhone("+212612345678"))
        assertEquals("", formatMoroccanPhone(""))
    }
}
