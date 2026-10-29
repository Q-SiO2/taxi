package org.example.taximobile.feature.ui.text

import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf

enum class TaxiLanguage(val tag: String, val nativeName: String) {
    English("en", "English"), French("fr", "Français"), Arabic("ar", "العربية");

    companion object {
        fun fromTag(value: String?): TaxiLanguage? = entries.firstOrNull {
            it.tag == value?.replace('_', '-')?.substringBefore('-')?.lowercase()
        }
    }
}

interface TaxiLanguageStore {
    fun read(): String?
    fun write(value: String)
}

/** A local display preference. It never owns or recreates an application session. */
@Stable
class TaxiLanguagePreferences(
    private val store: TaxiLanguageStore,
    systemLanguage: String? = null,
    private val applyLanguage: (TaxiLanguage) -> Boolean = { true },
) {
    var language by mutableStateOf(TaxiLanguage.fromTag(systemLanguage) ?: TaxiLanguage.English)
        private set
    var storageFailed by mutableStateOf(false)
        private set
    var changeFailed by mutableStateOf(false)
        private set

    init {
        val stored = try { TaxiLanguage.fromTag(store.read()) } catch (_: Exception) {
            storageFailed = true
            null
        }
        val initial = stored ?: language
        if (applyLanguage(initial)) language = initial else changeFailed = true
    }

    fun select(value: TaxiLanguage) {
        if (!applyLanguage(value)) {
            changeFailed = true
            return
        }
        changeFailed = false
        language = value
        try {
            store.write(value.tag)
            storageFailed = false
        } catch (_: Exception) { storageFailed = true }
    }
}

val LocalTaxiLanguagePreferences = staticCompositionLocalOf<TaxiLanguagePreferences?> { null }
