package org.example.taximobile.feature.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/** Presentation only. Never key a session, coordinator or request by this value. */
enum class TaxiStyle(val storageValue: String) {
    FoldedStreets("folded_streets"),
    StreetPress("street_press"),
    GlazedMachine("glazed_machine"),
    Notepad("notepad");

    val decorativeMotion: Boolean get() = this != Notepad

    companion object {
        fun fromStorage(value: String?): TaxiStyle = entries.firstOrNull { it.storageValue == value } ?: FoldedStreets
    }
}

interface TaxiStyleStore {
    fun read(): String?
    fun write(value: String)
}

@Stable
class TaxiStylePreferences(private val store: TaxiStyleStore) {
    var style by mutableStateOf(TaxiStyle.FoldedStreets)
        private set
    var storageFailed by mutableStateOf(false)
        private set

    init {
        try { style = TaxiStyle.fromStorage(store.read()) } catch (_: Exception) { storageFailed = true }
    }

    /** Keep the chosen presentation even if disk is unavailable; disclose that it is temporary. */
    fun select(value: TaxiStyle) {
        style = value
        try {
            store.write(value.storageValue)
            storageFailed = false
        } catch (_: Exception) { storageFailed = true }
    }
}

@Composable
expect fun rememberTaxiStylePreferences(): TaxiStylePreferences

data class TaxiCornerRadii(val Sm: Dp, val Md: Dp, val Lg: Dp, val Xl: Dp, val Pill: Dp)

fun TaxiStyle.cornerRadii(): TaxiCornerRadii = when (this) {
    TaxiStyle.FoldedStreets -> TaxiCornerRadii(2.dp, 4.dp, 6.dp, 8.dp, 8.dp)
    TaxiStyle.StreetPress, TaxiStyle.Notepad -> TaxiCornerRadii(0.dp, 0.dp, 0.dp, 0.dp, 0.dp)
    TaxiStyle.GlazedMachine -> TaxiCornerRadii(12.dp, 16.dp, 24.dp, 32.dp, 999.dp)
}
