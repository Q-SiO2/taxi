package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.sizeIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
fun TaxiTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    isError: Boolean = false,
    supportingText: String? = null,
    password: Boolean = false,
    readOnly: Boolean = false,
    keyboardType: KeyboardType = KeyboardType.Text,
    imeAction: ImeAction = ImeAction.Next,
    leadingContent: (@Composable () -> Unit)? = null,
) {
    var passwordVisible by remember { mutableStateOf(false) }
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier.fillMaxWidth().sizeIn(minHeight = 56.dp),
        enabled = enabled,
        readOnly = readOnly,
        label = { Text(label) },
        isError = isError,
        supportingText = supportingText?.let { text -> ({ Text(text) }) },
        visualTransformation = if (password && !passwordVisible) PasswordVisualTransformation() else VisualTransformation.None,
        trailingIcon = if (password) {
            {
                TextButton(onClick = { passwordVisible = !passwordVisible }) {
                    Text(stringResource(if (passwordVisible) Res.string.hide_password else Res.string.show_password))
                }
            }
        } else {
            null
        },
        leadingIcon = leadingContent,
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType, imeAction = imeAction),
        shape = RoundedCornerShape(TaxiRadii.Md),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = TaxiColors.Navy900,
            unfocusedBorderColor = TaxiColors.StrokeSubtle,
            errorBorderColor = TaxiColors.Danger600,
            errorSupportingTextColor = TaxiColors.Danger600,
        ),
        singleLine = true,
    )
}
