package org.example.taximobile.feature.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import platform.Foundation.NSUserDefaults

@Composable
actual fun rememberTaxiStylePreferences(): TaxiStylePreferences = remember {
    TaxiStylePreferences(object : TaxiStyleStore {
        override fun read(): String? = NSUserDefaults.standardUserDefaults.stringForKey("taximobile.presentation.style")
        override fun write(value: String) {
            NSUserDefaults.standardUserDefaults.setObject(value, forKey = "taximobile.presentation.style")
        }
    })
}
