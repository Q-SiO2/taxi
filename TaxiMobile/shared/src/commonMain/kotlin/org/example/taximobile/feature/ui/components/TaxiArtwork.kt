package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing

/**
 * Asset-independent brand artwork. Screens use this whenever no approved
 * illustration is bundled, so missing optional images never create blank or
 * inaccessible states.
 */
@Composable
fun TaxiBrandArtwork(
    contentDescriptionText: String,
    modifier: Modifier = Modifier,
) {
    Canvas(
        modifier = modifier.fillMaxWidth().heightIn(max = 220.dp).aspectRatio(1.55f).semantics {
            contentDescription = contentDescriptionText
        },
    ) {
        drawRoundRect(TaxiColors.Navy100, cornerRadius = CornerRadius(size.minDimension * 0.08f))
        val skyline = listOf(0.10f to 0.42f, 0.24f to 0.32f, 0.39f to 0.48f, 0.56f to 0.28f, 0.75f to 0.40f)
        skyline.forEachIndexed { index, (x, height) ->
            drawRoundRect(
                color = if (index % 2 == 0) TaxiColors.Navy200 else TaxiColors.Navy300,
                topLeft = Offset(size.width * x, size.height * (0.72f - height)),
                size = Size(size.width * 0.12f, size.height * height),
                cornerRadius = CornerRadius(size.minDimension * 0.015f),
            )
        }
        val route = Path().apply {
            moveTo(size.width * 0.08f, size.height * 0.82f)
            cubicTo(
                size.width * 0.30f, size.height * 0.58f,
                size.width * 0.61f, size.height * 0.96f,
                size.width * 0.91f, size.height * 0.67f,
            )
        }
        drawPath(route, TaxiColors.Accent500, style = androidx.compose.ui.graphics.drawscope.Stroke(size.minDimension * 0.035f))
        drawRoundRect(
            color = TaxiColors.Navy900,
            topLeft = Offset(size.width * 0.38f, size.height * 0.58f),
            size = Size(size.width * 0.30f, size.height * 0.17f),
            cornerRadius = CornerRadius(size.minDimension * 0.05f),
        )
        drawRoundRect(
            color = TaxiColors.Accent500,
            topLeft = Offset(size.width * 0.49f, size.height * 0.535f),
            size = Size(size.width * 0.08f, size.height * 0.05f),
            cornerRadius = CornerRadius(size.minDimension * 0.012f),
        )
        drawCircle(TaxiColors.Navy950, size.minDimension * 0.035f, Offset(size.width * 0.45f, size.height * 0.76f))
        drawCircle(TaxiColors.Navy950, size.minDimension * 0.035f, Offset(size.width * 0.62f, size.height * 0.76f))
    }
}

@Composable
fun EmptyState(
    title: String,
    body: String,
    modifier: Modifier = Modifier,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(TaxiRadii.Lg),
        color = TaxiColors.Surface1,
        border = androidx.compose.foundation.BorderStroke(1.dp, TaxiColors.StrokeSubtle),
    ) {
        androidx.compose.foundation.layout.Column(
            Modifier.padding(TaxiSpacing.Lg),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            Box(
                Modifier.background(TaxiColors.Accent100, RoundedCornerShape(TaxiRadii.Pill)).padding(TaxiSpacing.Md),
                contentAlignment = Alignment.Center,
            ) { Text(title.take(1), color = TaxiColors.Navy900, style = MaterialTheme.typography.titleLarge) }
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(body, style = MaterialTheme.typography.bodyMedium, color = TaxiColors.Ink500)
            if (actionLabel != null && onAction != null) {
                TaxiButton(actionLabel, onAction, style = TaxiButtonStyle.Secondary)
            }
        }
    }
}
