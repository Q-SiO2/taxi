package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.LocalTaxiStylePreferences
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

fun TaxiStyle.displayName(): String = when (this) {
    TaxiStyle.FoldedStreets -> "Folded Streets"
    TaxiStyle.StreetPress -> "Street Press"
    TaxiStyle.GlazedMachine -> "Glazed Machine"
    TaxiStyle.Notepad -> "Notepad"
}

/** Local presentation choice, deliberately independent of AppAction and session state. */
@Composable
fun TaxiStyleChooser(modifier: Modifier = Modifier) {
    val preferences = LocalTaxiStylePreferences.current ?: return
    var open by remember { mutableStateOf(false) }
    Column(modifier) {
        TextButton(onClick = { open = true }, modifier = Modifier.testTag("style-open")) {
            Text(stringResource(Res.string.presentation_style) + " · " + preferences.style.displayName())
        }
        if (preferences.storageFailed) {
            Text(stringResource(Res.string.style_storage_unavailable), color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall)
        }
    }
    if (open) {
        AlertDialog(
            onDismissRequest = { open = false },
            title = { Text(stringResource(Res.string.presentation_style)) },
            text = {
                Column(Modifier.selectableGroup(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    TaxiStyle.entries.forEach { style ->
                        Row(Modifier.fillMaxWidth().testTag("style-${style.storageValue}")
                            .selectable(selected = preferences.style == style, role = Role.RadioButton,
                                onClick = { preferences.select(style) }).padding(vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            RadioButton(selected = preferences.style == style, onClick = null)
                            Text(style.displayName(), modifier = Modifier.padding(start = 8.dp))
                        }
                    }
                    Text(stringResource(Res.string.style_local_note), style = MaterialTheme.typography.bodySmall)
                    if (preferences.style == TaxiStyle.Notepad) {
                        Text(stringResource(Res.string.style_notepad_note), style = MaterialTheme.typography.bodySmall)
                    }
                }
            },
            confirmButton = { TextButton(onClick = { open = false }) { Text(stringResource(Res.string.style_done)) } },
        )
    }
}
