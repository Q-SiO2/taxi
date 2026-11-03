package org.example.taximobile.feature.ui.components

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
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
    confirmEnabled: Boolean = true,
) {
    val taxiColors = TaxiTheme.colors
    AlertDialog(
        onDismissRequest = onCancel,
        shape = RoundedCornerShape(TaxiTheme.radii.Xl),
        title = { Text(title) },
        text = { Text(body) },
        confirmButton = {
            Button(
                onClick = onConfirm,
                enabled = confirmEnabled,
                shape = RoundedCornerShape(TaxiTheme.radii.Md),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (destructive) taxiColors.Danger600 else taxiColors.Accent500,
                    contentColor = if (destructive) MaterialTheme.colorScheme.onError
                        else MaterialTheme.colorScheme.onPrimary,
                ),
            ) { Text(confirmLabel) }
        },
        dismissButton = {
            TextButton(
                onClick = onCancel,
                shape = RoundedCornerShape(TaxiTheme.radii.Md),
                colors = ButtonDefaults.textButtonColors(contentColor = taxiColors.Navy900),
            ) { Text(stringResource(Res.string.keep_current_state)) }
        },
        containerColor = taxiColors.Surface0,
        titleContentColor = taxiColors.Navy900,
        textContentColor = taxiColors.Ink700,
    )
}
