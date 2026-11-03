package org.example.taximobile.feature.ui.components

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing

/**
 * Selected landing artwork with an asset-independent Compose fallback. The
 * fallback is used while loading and when optional artwork is missing/corrupt.
 * Runtime PNGs are used because Android cannot decode SVG resources. The
 * selected generated thin-line portrait and its prompt record live in assets/.
 */
@Composable
fun TaxiBrandArtwork(
    contentDescriptionText: String,
    modifier: Modifier = Modifier,
    useBundledAsset: Boolean = true,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    val painter = rememberOptionalArtworkPainter(BundledArtwork.Landing, useBundledAsset)
    // A phone-sized portrait, not a wide image squeezed into a short band.
    // The whole scene stays visible; narrow screens shrink it proportionally.
    Box(modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        val artworkModifier = Modifier.widthIn(max = 216.dp).fillMaxWidth()
            .aspectRatio(9f / 16f).clip(RoundedCornerShape(taxiRadii.Xl))
            .background(taxiColors.Navy900)
        if (painter != null) {
            Image(
                painter = painter,
                contentDescription = contentDescriptionText,
                modifier = artworkModifier,
                contentScale = ContentScale.Fit,
            )
        } else {
            TaxiBrandFallbackArtwork(contentDescriptionText, artworkModifier)
        }
    }
}

@Composable
private fun TaxiBrandFallbackArtwork(
    contentDescriptionText: String,
    modifier: Modifier,
) {
    val taxiColors = TaxiTheme.colors
    Canvas(
        modifier = modifier.semantics {
            contentDescription = contentDescriptionText
        },
    ) {
        // Asset-independent emergency drawing, not operational route geometry.
        val outline = Stroke(size.minDimension * 0.007f)
        drawRect(taxiColors.Navy900)
        drawRoundRect(
            color = taxiColors.Navy300.copy(alpha = 0.65f),
            topLeft = Offset(size.width * 0.68f, size.height * 0.17f),
            size = Size(size.width * 0.12f, size.height * 0.43f),
            cornerRadius = CornerRadius.Zero,
            style = outline,
        )
        drawLine(taxiColors.Navy300.copy(alpha = 0.65f), Offset(size.width * 0.14f, size.height * 0.60f), Offset(size.width * 0.86f, size.height * 0.60f), outline.width)
        val roof = Path().apply {
            moveTo(size.width * 0.30f, size.height * 0.62f)
            lineTo(size.width * 0.41f, size.height * 0.50f)
            lineTo(size.width * 0.60f, size.height * 0.50f)
            lineTo(size.width * 0.74f, size.height * 0.62f)
        }
        drawPath(roof, taxiColors.Navy900)
        drawPath(roof, taxiColors.Navy300, style = outline)
        drawRoundRect(
            color = taxiColors.Navy900,
            topLeft = Offset(size.width * 0.18f, size.height * 0.62f),
            size = Size(size.width * 0.66f, size.height * 0.15f),
            cornerRadius = CornerRadius(size.minDimension * 0.035f),
        )
        drawRoundRect(
            color = taxiColors.Navy300,
            topLeft = Offset(size.width * 0.18f, size.height * 0.62f),
            size = Size(size.width * 0.66f, size.height * 0.15f),
            cornerRadius = CornerRadius(size.minDimension * 0.035f),
            style = outline,
        )
        drawRoundRect(
            color = taxiColors.Navy300,
            topLeft = Offset(size.width * 0.47f, size.height * 0.465f),
            size = Size(size.width * 0.08f, size.height * 0.03f),
            cornerRadius = CornerRadius(size.minDimension * 0.006f),
            style = outline,
        )
        for (x in listOf(0.32f, 0.70f)) {
            val center = Offset(size.width * x, size.height * 0.77f)
            drawCircle(taxiColors.Navy900, size.minDimension * 0.052f, center)
            drawCircle(taxiColors.Navy300, size.minDimension * 0.052f, center, style = outline)
        }
    }
}

@Composable
fun EmptyState(
    title: String,
    body: String,
    modifier: Modifier = Modifier,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
    useBundledBrandMark: Boolean = true,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    val brandPainter = rememberOptionalArtworkPainter(BundledArtwork.BrandMark, useBundledBrandMark)
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(taxiRadii.Lg),
        color = taxiColors.Surface1,
        border = androidx.compose.foundation.BorderStroke(1.dp, taxiColors.StrokeSubtle),
    ) {
        androidx.compose.foundation.layout.Column(
            Modifier.padding(TaxiSpacing.Lg),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            Box(
                Modifier.background(taxiColors.Accent100, RoundedCornerShape(taxiRadii.Pill)).padding(TaxiSpacing.Md),
                contentAlignment = Alignment.Center,
            ) {
                if (brandPainter != null) {
                    Image(
                        painter = brandPainter,
                        contentDescription = null,
                        modifier = Modifier.size(32.dp),
                    )
                } else {
                    Text(title.take(1), color = taxiColors.Navy900, style = MaterialTheme.typography.titleLarge)
                }
            }
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(body, style = MaterialTheme.typography.bodyMedium, color = taxiColors.Ink500)
            if (actionLabel != null && onAction != null) {
                TaxiButton(actionLabel, onAction, style = TaxiButtonStyle.Secondary)
            }
        }
    }
}
