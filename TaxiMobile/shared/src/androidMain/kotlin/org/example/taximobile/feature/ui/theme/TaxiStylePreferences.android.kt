package org.example.taximobile.feature.ui.theme

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext

@Composable
actual fun rememberTaxiStylePreferences(): TaxiStylePreferences {
    val context = LocalContext.current.applicationContext
    return remember(context) {
        TaxiStylePreferences(object : TaxiStyleStore {
            private val preferences = context.getSharedPreferences("taximobile.presentation", Context.MODE_PRIVATE)
            override fun read(): String? = preferences.getString("style", null)
            override fun write(value: String) {
                check(preferences.edit().putString("style", value).commit()) { "Style could not be saved" }
            }
        })
    }
}
