package org.example.taximobile.feature.ui.components

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.keep_current_state

@Composable
fun ConfirmDialog(
    title: String,
    body: String,
    confirmLabel: String,
    onConfirm: () -> Unit,
    onCancel: () -> Unit,
    destructive: Boolean = false,
) {
    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text(title) },
        text = { Text(body) },
        confirmButton = {
            TextButton(
                onClick = onConfirm,
                colors = ButtonDefaults.textButtonColors(contentColor = if (destructive) TaxiColors.Danger600 else TaxiColors.Navy900),
            ) { Text(confirmLabel) }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text(stringResource(Res.string.keep_current_state)) }
        },
    )
}
