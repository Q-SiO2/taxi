package org.example.taximobile.feature.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

object TaxiSpacing {
    val Xxs = 4.dp
    val Xs = 8.dp
    val Sm = 12.dp
    val Md = 16.dp
    val Lg = 20.dp
    val Xl = 24.dp
    val Xxl = 32.dp
    val Xxxl = 40.dp
    val Xxxxl = 48.dp
    val Huge = 64.dp
}

object TaxiRadii {
    val Sm = 8.dp
    val Md = 12.dp
    val Lg = 16.dp
    val Xl = 24.dp
    val Pill = 999.dp
}

internal val TaxiShapes = Shapes(
    extraSmall = RoundedCornerShape(TaxiRadii.Sm),
    small = RoundedCornerShape(TaxiRadii.Sm),
    medium = RoundedCornerShape(TaxiRadii.Md),
    large = RoundedCornerShape(TaxiRadii.Lg),
    extraLarge = RoundedCornerShape(TaxiRadii.Xl),
)
