package org.example.taximobile

import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import kotlin.js.ExperimentalWasmJsInterop
import kotlin.js.js
import org.example.taximobile.feature.ui.text.LocalTaxiLanguagePreferences
import org.example.taximobile.feature.ui.text.TaxiLanguage
import org.example.taximobile.feature.ui.text.TaxiLanguagePreferences
import org.example.taximobile.feature.ui.text.TaxiLanguageStore

@OptIn(ExperimentalWasmJsInterop::class)
private fun readLanguage(): String = js("""{ try { return localStorage.getItem('taximobile.presentation.language') || ''; } catch(e) { return '!storage-unavailable'; } }""")

@OptIn(ExperimentalWasmJsInterop::class)
private fun writeLanguage(value: String): Boolean = js("""{ try { localStorage.setItem('taximobile.presentation.language', value); return true; } catch(e) { return false; } }""")

@OptIn(ExperimentalWasmJsInterop::class)
private fun systemLanguage(): String = js("""{ return navigator.languages[0] || navigator.language || 'en'; }""")

@OptIn(ExperimentalWasmJsInterop::class)
private fun applyLanguage(value: String): Boolean = js("""{ return typeof window.taximobileSetLocale === 'function' && window.taximobileSetLocale(value); }""")

// A changed static local invalidates presentation without disposing remember scopes.
// In particular, never use key(language) around coordinators or safe form drafts.
private val LocalWebResourceLanguage = staticCompositionLocalOf { TaxiLanguage.English }

@Composable
fun WebLanguageEnvironment(content: @Composable () -> Unit) {
    val preferences = remember {
        TaxiLanguagePreferences(object : TaxiLanguageStore {
            override fun read(): String? = readLanguage().also { check(it != "!storage-unavailable") }
            override fun write(value: String) { check(writeLanguage(value)) }
        }, systemLanguage(), { applyLanguage(it.tag) })
    }
    CompositionLocalProvider(
        LocalWebResourceLanguage provides preferences.language,
        LocalTaxiLanguagePreferences provides preferences,
        LocalLayoutDirection provides if (preferences.language == TaxiLanguage.Arabic) LayoutDirection.Rtl else LayoutDirection.Ltr,
    ) { content() }
}
