package org.example.taximobile.applicant.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.example.taximobile.applicant.state.ApplicantPortalMessage
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing

@Composable
internal fun ApplicantWordmark(dark: Boolean = false) {
    val foreground = if (dark) Color.White else TaxiColors.Navy950
    Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm), verticalAlignment = Alignment.CenterVertically) {
        Surface(shape = CircleShape, color = TaxiColors.Accent500) {
            Text(
                "TM",
                modifier = Modifier.padding(horizontal = TaxiSpacing.Sm, vertical = TaxiSpacing.Xs),
                color = TaxiColors.Navy950,
                fontWeight = FontWeight.Black,
            )
        }
        Column {
            Text("TaxiMobile", color = foreground, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("DRIVER APPLICATIONS", color = if (dark) TaxiColors.Navy200 else TaxiColors.Ink500,
                style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
internal fun ApplicantCard(
    modifier: Modifier = Modifier,
    selected: Boolean = false,
    content: @Composable () -> Unit,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = if (selected) TaxiColors.Accent100 else TaxiColors.Surface0,
        shape = RoundedCornerShape(TaxiRadii.Lg),
        border = BorderStroke(if (selected) 2.dp else 1.dp, if (selected) TaxiColors.Accent500 else TaxiColors.StrokeSubtle),
        shadowElevation = if (selected) 3.dp else 1.dp,
    ) {
        Column(Modifier.padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            content()
        }
    }
}

@Composable
internal fun ApplicantMessageBanner(
    message: ApplicantPortalMessage,
    error: Boolean,
    onDismiss: () -> Unit,
) {
    Surface(
        color = if (error) TaxiColors.Danger100 else TaxiColors.Success100,
        shape = RoundedCornerShape(TaxiRadii.Md),
        border = BorderStroke(
            1.dp,
            (if (error) TaxiColors.Danger600 else TaxiColors.Success600).copy(alpha = 0.25f),
        ),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(message.title, fontWeight = FontWeight.Bold, color = TaxiColors.Navy900)
                Text(message.detail, style = MaterialTheme.typography.bodySmall, color = TaxiColors.Ink500)
            }
            OutlinedButton(onClick = onDismiss) { Text("Dismiss") }
        }
    }
}

@Composable
internal fun ApplicantPrimaryButton(
    label: String,
    onClick: () -> Unit,
    enabled: Boolean = true,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth(),
        colors = ButtonDefaults.buttonColors(
            containerColor = TaxiColors.Navy900,
            contentColor = Color.White,
            disabledContainerColor = TaxiColors.Ink300,
        ),
    ) { Text(label) }
}

@Composable
internal fun ApplicantStatus(status: String) {
    val (label, color) = when (status) {
        "APPROVED" -> "Approved" to TaxiColors.Success600
        "REJECTED", "WITHDRAWN", "SUSPENDED", "EXPIRED" -> status.toDisplayLabel() to TaxiColors.Danger600
        "ADDITIONAL_INFORMATION_REQUIRED" -> "More information required" to TaxiColors.Warning600
        else -> status.toDisplayLabel() to TaxiColors.Navy700
    }
    Surface(color = color.copy(alpha = 0.12f), shape = CircleShape) {
        Text(label, Modifier.padding(horizontal = TaxiSpacing.Sm, vertical = TaxiSpacing.Xs), color = color,
            style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
    }
}

internal fun String.toDisplayLabel(): String = lowercase()
    .split('_')
    .joinToString(" ") { word -> word.replaceFirstChar { it.uppercase() } }
