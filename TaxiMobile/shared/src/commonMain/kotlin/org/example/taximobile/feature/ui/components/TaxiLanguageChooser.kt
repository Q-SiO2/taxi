package org.example.taximobile.feature.ui.components

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
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.text.LocalTaxiLanguagePreferences
import org.example.taximobile.feature.ui.text.TaxiLanguage
import org.example.taximobile.feature.ui.theme.taxiArabicFontFamily
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
fun TaxiLanguageChooser(modifier: Modifier = Modifier) {
    val preferences = LocalTaxiLanguagePreferences.current ?: return
    var open by remember { mutableStateOf(false) }
    val title = stringResource(Res.string.presentation_language)
    Column(modifier) {
        TextButton(onClick = { open = true }, modifier = Modifier.testTag("language-open")
            .semantics { contentDescription = title }) {
            Text(preferences.language.nativeName,
                fontFamily = if (preferences.language == TaxiLanguage.Arabic) taxiArabicFontFamily() else null)
        }
        if (preferences.storageFailed || preferences.changeFailed) {
            Text(stringResource(if (preferences.changeFailed) Res.string.language_change_unavailable
                else Res.string.language_storage_unavailable), color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall)
        }
    }
    if (open) {
        AlertDialog(
            onDismissRequest = { open = false },
            title = { Text(title) },
            text = {
                Column(Modifier.selectableGroup()) {
                    TaxiLanguage.entries.forEach { language ->
                        Row(Modifier.fillMaxWidth().testTag("language-${language.tag}")
                            .selectable(selected = preferences.language == language, role = Role.RadioButton,
                                onClick = { preferences.select(language) }).padding(vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            RadioButton(selected = preferences.language == language, onClick = null)
                            Text(language.nativeName, Modifier.padding(start = 8.dp),
                                fontFamily = if (language == TaxiLanguage.Arabic) taxiArabicFontFamily() else null)
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { open = false }) { Text(stringResource(Res.string.style_done)) } },
        )
    }
}
