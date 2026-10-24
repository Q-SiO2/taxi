package org.example.taximobile.feature.ui.components

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.loading

enum class TaxiButtonStyle { Primary, Secondary, Tertiary, Destructive, ToneLike }

@Composable
fun TaxiButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    loading: Boolean = false,
    style: TaxiButtonStyle = TaxiButtonStyle.Primary,
) {
    val taxiColors = TaxiTheme.colors
    val shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md)
    val loadingDescription = stringResource(Res.string.loading)
    val buttonModifier = modifier
        .fillMaxWidth()
        .defaultMinSize(minHeight = if (style == TaxiButtonStyle.Primary) 56.dp else 48.dp)
        .semantics { if (loading) stateDescription = loadingDescription }
    val content: @Composable () -> Unit = {
        Box(contentAlignment = Alignment.Center) {
            if (loading) {
                CircularProgressIndicator(
                    color = if (style == TaxiButtonStyle.Destructive || style == TaxiButtonStyle.Primary) Color.White else taxiColors.ink,
                    strokeWidth = 2.dp,
                    modifier = Modifier.defaultMinSize(minWidth = 20.dp, minHeight = 20.dp),
                )
            } else {
                Text(label)
            }
        }
    }
    when (style) {
        TaxiButtonStyle.Primary -> Button(
            shape = shape,
            onClick = onClick,
            modifier = buttonModifier,
            enabled = enabled && !loading,
            colors = ButtonDefaults.buttonColors(
                containerColor = taxiColors.Accent500,
                contentColor = Color.White,
                disabledContainerColor = taxiColors.Surface2,
                disabledContentColor = taxiColors.Ink300,
            ),
            content = { content() },
        )
        TaxiButtonStyle.Destructive -> Button(
            shape = shape,
            onClick = onClick,
            modifier = buttonModifier,
            enabled = enabled && !loading,
            colors = ButtonDefaults.buttonColors(containerColor = taxiColors.Danger600),
            content = { content() },
        )
        TaxiButtonStyle.Secondary -> OutlinedButton(
            shape = shape,
            onClick = onClick,
            modifier = buttonModifier,
            enabled = enabled && !loading,
            content = { content() },
        )
        TaxiButtonStyle.Tertiary -> TextButton(
            shape = shape,
            onClick = onClick,
            modifier = buttonModifier,
            enabled = enabled && !loading,
            content = { content() },
        )
        TaxiButtonStyle.ToneLike -> TextButton(
            shape = shape,
            onClick = onClick,
            modifier = buttonModifier,
            enabled = enabled && !loading,
            colors = ButtonDefaults.textButtonColors(
                containerColor = taxiColors.Accent100,
                contentColor = taxiColors.Accent600,
            ),
            content = { content() },
        )
    }
}
