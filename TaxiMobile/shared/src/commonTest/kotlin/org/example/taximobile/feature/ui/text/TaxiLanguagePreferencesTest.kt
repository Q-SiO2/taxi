package org.example.taximobile.feature.ui.text

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class TaxiLanguagePreferencesTest {
    private class Store(var value: String? = null, var fail: Boolean = false) : TaxiLanguageStore {
        override fun read(): String? { check(!fail); return value }
        override fun write(value: String) { check(!fail); this.value = value }
    }

    @Test fun persisted_language_wins_and_all_three_choices_survive_restart() {
        val store = Store("ar")
        assertEquals(TaxiLanguage.Arabic, TaxiLanguagePreferences(store, "fr-MA").language)
        TaxiLanguage.entries.forEach { language ->
            TaxiLanguagePreferences(store).select(language)
            assertEquals(language, TaxiLanguagePreferences(store).language)
        }
    }

    @Test fun unknown_storage_uses_supported_system_language_then_english() {
        assertEquals(TaxiLanguage.French, TaxiLanguagePreferences(Store("bad"), "fr_MA").language)
        assertEquals(TaxiLanguage.English, TaxiLanguagePreferences(Store(), "de-DE").language)
        assertEquals(TaxiLanguage.Arabic, TaxiLanguagePreferences(Store(), "ar-MA").language)
    }

    @Test fun blocked_storage_keeps_temporary_choice_and_a_successful_retry_clears_warning() {
        val store = Store(fail = true)
        val preferences = TaxiLanguagePreferences(store, "fr")
        assertTrue(preferences.storageFailed)
        preferences.select(TaxiLanguage.Arabic)
        assertEquals(TaxiLanguage.Arabic, preferences.language)
        assertTrue(preferences.storageFailed)
        store.fail = false
        preferences.select(TaxiLanguage.Arabic)
        assertFalse(preferences.storageFailed)
        assertEquals(TaxiLanguage.Arabic, TaxiLanguagePreferences(store).language)
    }

    @Test fun failed_platform_change_retains_applied_language_and_does_not_persist_it() {
        val store = Store("fr")
        var available = true
        val preferences = TaxiLanguagePreferences(store, "en") { available }
        available = false
        preferences.select(TaxiLanguage.Arabic)
        assertEquals(TaxiLanguage.French, preferences.language)
        assertEquals("fr", store.value)
        assertTrue(preferences.changeFailed)
        available = true
        preferences.select(TaxiLanguage.Arabic)
        assertFalse(preferences.changeFailed)
        assertEquals("ar", store.value)
    }
}
