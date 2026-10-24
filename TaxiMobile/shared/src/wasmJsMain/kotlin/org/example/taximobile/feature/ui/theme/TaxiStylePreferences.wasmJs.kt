package org.example.taximobile.feature.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import kotlin.js.ExperimentalWasmJsInterop
import kotlin.js.js

// Catch browser DOM exceptions in JS so blocked storage reaches the visible recovery state.
@OptIn(ExperimentalWasmJsInterop::class)
private fun readStyle(): String = js("""{ try { return localStorage.getItem('taximobile.presentation.style') || ''; } catch(e) { return '!storage-unavailable'; } }""")

@OptIn(ExperimentalWasmJsInterop::class)
private fun writeStyle(value: String): Boolean = js("""{ try { localStorage.setItem('taximobile.presentation.style', value); return true; } catch(e) { return false; } }""")

@Composable
actual fun rememberTaxiStylePreferences(): TaxiStylePreferences = remember {
    TaxiStylePreferences(object : TaxiStyleStore {
        override fun read(): String? = readStyle().also { check(it != "!storage-unavailable") }
        override fun write(value: String) { check(writeStyle(value)) { "Style could not be saved" } }
    })
}
