package org.example.taximobile.feature.ui.text

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import kotlin.test.assertFalse

class BidiTextTest {
    @Test
    fun machine_identifier_is_wrapped_in_ltr_isolate_controls() {
        assertEquals("\u2066TX-1234\u2069", ltrIsolate("TX-1234"))
    }

    @Test
    fun mixed_applicant_content_selects_an_arabic_capable_font_in_every_ui_language() {
        assertTrue(hasArabicScript("Salma سلمى 123"))
        assertTrue(hasArabicScript("\u0750"))
        assertTrue(hasArabicScript("\u08a0"))
        assertTrue(hasArabicScript("\ufb50"))
        assertTrue(hasArabicScript("\ufe70"))
        assertFalse(hasArabicScript("Salma — Casablanca 2026-10-18"))
        assertFalse(hasArabicScript(""))
    }
}
