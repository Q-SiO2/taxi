package org.example.taximobile.feature.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import java.util.prefs.Preferences

@Composable
actual fun rememberTaxiStylePreferences(): TaxiStylePreferences = remember {
    TaxiStylePreferences(object : TaxiStyleStore {
        private val preferences by lazy { Preferences.userRoot().node("org/example/taximobile/presentation") }
        override fun read(): String? = preferences.get("style", null)
        override fun write(value: String) { preferences.put("style", value); preferences.flush() }
    })
}
