package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.drawscope.Stroke
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.jetbrains.compose.resources.painterResource
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.vehicle_silhouette_standard

@Composable
fun TaxiCard(
    modifier: Modifier = Modifier,
    selected: Boolean = false,
    content: @Composable () -> Unit,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(TaxiRadii.Lg),
        color = if (selected) TaxiColors.Accent100 else TaxiColors.Surface0,
        border = BorderStroke(if (selected) 2.dp else 1.dp, if (selected) TaxiColors.Accent500 else TaxiColors.StrokeSubtle),
        shadowElevation = if (selected) 3.dp else 1.dp,
    ) {
        Column(
            Modifier.padding(TaxiSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
            content = { content() },
        )
    }
}

@Composable
fun LocationSelectionField(
    label: String,
    value: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier.fillMaxWidth().defaultMinSize(minHeight = 64.dp)
            .semantics {
                role = Role.RadioButton
                this.selected = selected
            }
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(TaxiRadii.Md),
        color = if (selected) TaxiColors.Accent100 else TaxiColors.Surface0,
        border = BorderStroke(if (selected) 2.dp else 1.dp, if (selected) TaxiColors.Accent500 else TaxiColors.StrokeSubtle),
    ) {
        Row(
            Modifier.padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Sm),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Canvas(Modifier.size(20.dp)) {
                if (selected) {
                    drawCircle(TaxiColors.Accent500)
                    drawCircle(TaxiColors.Navy900, radius = size.minDimension * 0.18f)
                } else {
                    drawCircle(TaxiColors.Navy900, style = Stroke(width = 2.dp.toPx()))
                }
            }
            Column(Modifier.weight(1f)) {
                Text(label, style = MaterialTheme.typography.labelMedium, color = TaxiColors.Ink500)
                Text(value, style = MaterialTheme.typography.bodyLarge, color = TaxiColors.Ink900)
            }
        }
    }
}

@Composable
fun DriverDocumentCard(
    title: String,
    status: String,
    detail: String?,
    modifier: Modifier = Modifier,
) {
    TaxiCard(modifier) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(status, style = MaterialTheme.typography.labelMedium, color = TaxiColors.Navy700)
        }
        detail?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = TaxiColors.Ink500) }
    }
}

@Composable
fun PaymentMethodCard(
    label: String,
    detail: String,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
) {
    val interactionModifier = if (onClick == null) {
        Modifier
    } else {
        Modifier
            .semantics {
                role = Role.RadioButton
                this.selected = selected
            }
            .clickable(onClick = onClick)
    }
    TaxiCard(modifier.then(interactionModifier), selected = selected) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                modifier = Modifier.defaultMinSize(minWidth = 44.dp, minHeight = 44.dp),
                shape = RoundedCornerShape(TaxiRadii.Md),
                color = TaxiColors.Navy900,
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(label.take(1), color = TaxiColors.Surface0, style = MaterialTheme.typography.titleSmall)
                }
            }
            Column(Modifier.weight(1f)) {
                Text(label, style = MaterialTheme.typography.titleSmall)
                Text(detail, style = MaterialTheme.typography.bodyMedium, color = TaxiColors.Ink500)
            }
            StatusPill(label, if (selected) StatusTone.Accent else StatusTone.Neutral)
        }
    }
}

@Composable
fun VehicleAssetFallback(
    vehicleLabel: String,
    modifier: Modifier = Modifier,
    useBundledAsset: Boolean = true,
) {
    Surface(
        modifier = modifier.defaultMinSize(minWidth = 72.dp, minHeight = 44.dp),
        shape = RoundedCornerShape(TaxiRadii.Md),
        color = TaxiColors.Navy100,
        border = BorderStroke(1.dp, TaxiColors.Navy200),
    ) {
        Box(Modifier.padding(TaxiSpacing.Xs), contentAlignment = Alignment.Center) {
            if (useBundledAsset) {
                Image(
                    painter = painterResource(Res.drawable.vehicle_silhouette_standard),
                    contentDescription = vehicleLabel,
                    modifier = Modifier.size(width = 72.dp, height = 44.dp),
                    contentScale = ContentScale.Fit,
                )
            } else {
                Text(
                    vehicleLabel.take(2).uppercase(),
                    style = MaterialTheme.typography.labelLarge,
                    color = TaxiColors.Navy900,
                )
            }
        }
    }
}
