package org.example.taximobile.feature.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import kotlinx.browser.window

@Composable
actual fun rememberTaxiStylePreferences(): TaxiStylePreferences = remember {
    TaxiStylePreferences(object : TaxiStyleStore {
        override fun read(): String? = window.localStorage.getItem("taximobile.presentation.style")
        override fun write(value: String) { window.localStorage.setItem("taximobile.presentation.style", value) }
    })
}
