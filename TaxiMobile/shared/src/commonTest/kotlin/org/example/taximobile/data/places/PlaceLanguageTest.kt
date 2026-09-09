package org.example.taximobile.data.places

import kotlin.test.Test
import kotlin.test.assertEquals

class PlaceLanguageTest {
    @Test
    fun language_is_restricted_to_backend_contract() {
        assertEquals("ar", normalizedPlaceLanguage("ar-MA"))
        assertEquals("fr", normalizedPlaceLanguage("fr_FR"))
        assertEquals("en", normalizedPlaceLanguage("en-GB"))
        assertEquals("en", normalizedPlaceLanguage("de-DE"))
    }
}
