package org.example.taximobile.applicant.ui

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
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
import org.example.taximobile.feature.ui.text.resolve
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*
import org.example.taximobile.operations.ui.recruitmentLabel

@Composable
internal fun ApplicantWordmark(dark: Boolean = false) {
    val taxiColors = TaxiTheme.colors
    val foreground = if (dark) Color.White else taxiColors.Navy950
    Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm), verticalAlignment = Alignment.CenterVertically) {
        Surface(shape = RoundedCornerShape(TaxiTheme.radii.Md), color = taxiColors.Accent500) {
            Text(
                "TM",
                modifier = Modifier.padding(horizontal = TaxiSpacing.Sm, vertical = TaxiSpacing.Xs),
                color = MaterialTheme.colorScheme.onPrimary,
                fontWeight = FontWeight.Black,
            )
        }
        Column {
            Text("TaxiMobile", color = foreground, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text(stringResource(Res.string.web_driver_applications), color = if (dark) taxiColors.Navy200 else taxiColors.Ink500,
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
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = if (selected) taxiColors.Accent100 else taxiColors.Surface0,
        shape = RoundedCornerShape(taxiRadii.Lg),
        border = BorderStroke(if (selected) 2.dp else 1.dp, if (selected) taxiColors.Accent500 else taxiColors.StrokeSubtle),
        shadowElevation = if (TaxiTheme.style == org.example.taximobile.feature.ui.theme.TaxiStyle.Notepad) 0.dp else if (selected) 3.dp else 1.dp,
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
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Surface(
        color = if (error) taxiColors.Danger100 else taxiColors.Success100,
        shape = RoundedCornerShape(taxiRadii.Md),
        border = BorderStroke(
            1.dp,
            (if (error) taxiColors.Danger600 else taxiColors.Success600).copy(alpha = 0.25f),
        ),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(message.localizedTitle?.resolve() ?: message.title, fontWeight = FontWeight.Bold, color = taxiColors.Navy900)
                Text(message.localizedDetail?.resolve() ?: message.detail, style = MaterialTheme.typography.bodySmall, color = taxiColors.Ink500)
            }
            OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = onDismiss) { Text(stringResource(Res.string.web_dismiss)) }
        }
    }
}

@Composable
internal fun ApplicantPrimaryButton(
    label: String,
    onClick: () -> Unit,
    enabled: Boolean = true,
) {
    val taxiColors = TaxiTheme.colors
    Button(
        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth(),
        colors = ButtonDefaults.buttonColors(
            containerColor = taxiColors.Navy900,
            contentColor = Color.White,
            disabledContainerColor = taxiColors.Ink300,
        ),
    ) { Text(label) }
}

@Composable
internal fun ApplicantStatus(status: String) {
    val taxiColors = TaxiTheme.colors
    val color = when (status) {
        "APPROVED" -> taxiColors.Success600
        "REJECTED", "WITHDRAWN", "SUSPENDED", "EXPIRED" -> taxiColors.Danger600
        "ADDITIONAL_INFORMATION_REQUIRED" -> taxiColors.Warning600
        else -> taxiColors.Navy700
    }
    Surface(color = color.copy(alpha = 0.12f), shape = RoundedCornerShape(TaxiTheme.radii.Sm)) {
        Text(recruitmentLabel(status), Modifier.padding(horizontal = TaxiSpacing.Sm, vertical = TaxiSpacing.Xs), color = color,
            style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
    }
}

