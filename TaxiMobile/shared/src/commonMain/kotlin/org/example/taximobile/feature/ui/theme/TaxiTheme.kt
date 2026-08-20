package org.example.taximobile.feature.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf

private val LocalTaxiAdditionalTypography = staticCompositionLocalOf<TaxiAdditionalTypography> {
    error("TaxiTheme is required")
}

object TaxiTheme {
    val colors: TaxiColors
        @Composable get() = TaxiColors

    val typography: TaxiAdditionalTypography
        @Composable get() = LocalTaxiAdditionalTypography.current
}

@Composable
fun TaxiTheme(content: @Composable () -> Unit) {
    val (typography, additionalTypography) = taxiTypography()
    CompositionLocalProvider(LocalTaxiAdditionalTypography provides additionalTypography) {
        MaterialTheme(
            colorScheme = taxiLightColorScheme(),
            typography = typography,
            shapes = TaxiShapes,
            content = content,
        )
    }
}
