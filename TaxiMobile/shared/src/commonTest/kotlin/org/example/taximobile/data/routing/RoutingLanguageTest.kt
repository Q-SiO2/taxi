package org.example.taximobile.data.routing

import kotlin.test.Test
import kotlin.test.assertEquals

class RoutingLanguageTest {
    @Test
    fun supported_platform_languages_are_reduced_to_api_values() {
        assertEquals("fr", normalizedLanguage("fr-MA"))
        assertEquals("ar", normalizedLanguage("ar_MA"))
        assertEquals("en", normalizedLanguage("en-US"))
    }

    @Test
    fun unknown_or_blank_platform_languages_fail_closed_to_english() {
        assertEquals("en", normalizedLanguage("de-DE"))
        assertEquals("en", normalizedLanguage(""))
    }
}
