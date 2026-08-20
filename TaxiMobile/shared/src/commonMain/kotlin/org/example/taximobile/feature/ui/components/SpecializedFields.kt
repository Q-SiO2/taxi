package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing

@Composable
fun EmailField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    isError: Boolean = false,
    supportingText: String? = null,
) = TaxiTextField(
    value = value,
    onValueChange = { candidate -> onValueChange(candidate.filterNot(Char::isWhitespace)) },
    label = label,
    modifier = modifier,
    enabled = enabled,
    isError = isError,
    supportingText = supportingText,
    keyboardType = KeyboardType.Email,
)

@Composable
fun PasswordField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    supportingText: String? = null,
    imeAction: ImeAction = ImeAction.Done,
) = TaxiTextField(
    value = value,
    onValueChange = onValueChange,
    label = label,
    modifier = modifier,
    enabled = enabled,
    supportingText = supportingText,
    password = true,
    keyboardType = KeyboardType.Password,
    imeAction = imeAction,
)

@Composable
fun PhoneNumberField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    isError: Boolean = false,
    supportingText: String? = null,
) = TaxiTextField(
    value = formatMoroccanPhone(value),
    onValueChange = { onValueChange(normalizeMoroccanPhoneInput(it)) },
    label = label,
    modifier = modifier,
    enabled = enabled,
    isError = isError,
    supportingText = supportingText,
    keyboardType = KeyboardType.Phone,
)

internal fun normalizeMoroccanPhoneInput(value: String): String {
    val digits = value.filter(Char::isDigit)
    val national = when {
        digits.startsWith("00212") -> digits.drop(5)
        digits.startsWith("212") -> digits.drop(3)
        digits.startsWith("0") -> digits.drop(1)
        else -> digits
    }.take(9)
    return if (national.isBlank()) "" else "+212$national"
}

internal fun formatMoroccanPhone(value: String): String {
    val canonical = normalizeMoroccanPhoneInput(value)
    if (canonical.isBlank()) return ""
    val national = canonical.removePrefix("+212")
    return buildString {
        append("+212 | ")
        national.firstOrNull()?.let(::append)
        national.drop(1).chunked(2).forEach { chunk ->
            append(" ")
            append(chunk)
        }
    }
}

@Composable
fun OtpInput(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    length: Int = 6,
    enabled: Boolean = true,
    contentDescriptionText: String,
) {
    val digits = value.filter(Char::isDigit).take(length)
    BasicTextField(
        value = digits,
        onValueChange = { onValueChange(it.filter(Char::isDigit).take(length)) },
        enabled = enabled,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword, imeAction = ImeAction.Done),
        cursorBrush = SolidColor(TaxiColors.Navy900),
        modifier = modifier.fillMaxWidth().semantics { contentDescription = contentDescriptionText },
        decorationBox = { innerTextField ->
            Box {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                    repeat(length) { index ->
                        val selectedSlot = index == digits.length && digits.length < length
                        Surface(
                            modifier = Modifier.weight(1f).defaultMinSize(minHeight = 56.dp),
                            shape = RoundedCornerShape(TaxiRadii.Md),
                            color = TaxiColors.Surface0,
                            border = androidx.compose.foundation.BorderStroke(
                                if (selectedSlot) 2.dp else 1.dp,
                                if (selectedSlot) TaxiColors.Navy900 else TaxiColors.StrokeSubtle,
                            ),
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Text(digits.getOrNull(index)?.toString().orEmpty(), style = MaterialTheme.typography.titleLarge)
                            }
                        }
                    }
                }
                Box(Modifier.matchParentSize().alpha(0f)) { innerTextField() }
            }
        },
    )
}

@Composable
fun RatingStars(
    value: Int,
    onValueChange: (Int) -> Unit,
    scoreDescriptions: List<String>,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
        repeat(5) { index ->
            val score = index + 1
            Text(
                text = if (score <= value) "★" else "☆",
                color = if (score <= value) TaxiColors.Accent600 else TaxiColors.Ink300,
                style = MaterialTheme.typography.displaySmall,
                modifier = Modifier
                    .defaultMinSize(48.dp, 48.dp)
                    .semantics {
                        contentDescription = scoreDescriptions.getOrElse(index) { score.toString() }
                        role = Role.RadioButton
                        selected = score == value
                    }
                    .clickable(enabled = enabled) { onValueChange(score) }
                    .padding(TaxiSpacing.Xs),
            )
        }
    }
}
