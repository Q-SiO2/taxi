package org.example.taximobile.feature.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf

private val LocalTaxiAdditionalTypography = staticCompositionLocalOf<TaxiAdditionalTypography> { error("TaxiTheme is required") }
private val LocalTaxiStyle = staticCompositionLocalOf { TaxiStyle.FoldedStreets }
private val LocalTaxiPalette = staticCompositionLocalOf<TaxiPalette> { TaxiColors }
val LocalTaxiStylePreferences = staticCompositionLocalOf<TaxiStylePreferences?> { null }

object TaxiTheme {
    val colors: TaxiPalette @Composable get() = LocalTaxiPalette.current
    val style: TaxiStyle @Composable get() = LocalTaxiStyle.current
    val radii: TaxiCornerRadii @Composable get() = style.cornerRadii()
    val typography: TaxiAdditionalTypography @Composable get() = LocalTaxiAdditionalTypography.current
}

@Composable
fun TaxiTheme(
    style: TaxiStyle = LocalTaxiStylePreferences.current?.style ?: TaxiStyle.FoldedStreets,
    content: @Composable () -> Unit,
) {
    val (typography, additionalTypography) = taxiTypography(style)
    val colors = taxiPalette(style)
    val radii = style.cornerRadii()
    CompositionLocalProvider(LocalTaxiAdditionalTypography provides additionalTypography,
        LocalTaxiStyle provides style, LocalTaxiPalette provides colors) {
        MaterialTheme(
            colorScheme = taxiLightColorScheme(colors), typography = typography,
            shapes = Shapes(RoundedCornerShape(radii.Sm), RoundedCornerShape(radii.Sm),
                RoundedCornerShape(radii.Md), RoundedCornerShape(radii.Lg), RoundedCornerShape(radii.Xl)),
            content = content,
        )
    }
}
