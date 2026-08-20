package org.example.taximobile.feature.ui.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

/** The approved TaxiMobile palette from docs/ui.md. Feature code must use these semantic tokens. */
object TaxiColors {
    val Navy950 = Color(0xFF071426)
    val Navy900 = Color(0xFF0B1F3A)
    val Navy800 = Color(0xFF163A63)
    val Navy700 = Color(0xFF1B3554)
    val Navy600 = Color(0xFF27486D)
    val Navy500 = Color(0xFF3A5F8A)
    val Navy400 = Color(0xFF5E82AD)
    val Navy300 = Color(0xFF8AA6C5)
    val Navy200 = Color(0xFFC2D3E6)
    val Navy100 = Color(0xFFE4EDF7)
    val Navy50 = Color(0xFFF3F7FB)

    val Accent600 = Color(0xFF9B7900)
    val Accent500 = Color(0xFFD6A800)
    val Accent400 = Color(0xFFF3D76A)
    val Accent100 = Color(0xFFFFF5C2)

    val Success600 = Color(0xFF14804A)
    val Success100 = Color(0xFFDDF5E8)
    val Warning600 = Color(0xFFB7791F)
    val Warning100 = Color(0xFFFFF3D6)
    val Danger600 = Color(0xFFC53030)
    val Danger100 = Color(0xFFFDE8E8)
    val Info600 = Color(0xFF2B6CB0)
    val Info100 = Color(0xFFE6F0FA)

    val Surface0 = Color(0xFFFFFFFF)
    val Surface1 = Color(0xFFF6F8FB)
    val Surface2 = Color(0xFFEAECF0)
    val Ink900 = Navy900
    val Ink700 = Color(0xFF334155)
    val Ink500 = Color(0xFF64748B)
    val Ink300 = Color(0xFF94A3B8)
    val StrokeSubtle = Color(0xFFD9E0E8)
    val StrokeStrong = Color(0xFFA8B9CD)
    val Scrim = Navy900.copy(alpha = 0.40f)
    val MapOverlay = Navy900.copy(alpha = 0.12f)
}

internal fun taxiLightColorScheme(): ColorScheme = lightColorScheme(
    primary = TaxiColors.Accent500,
    onPrimary = TaxiColors.Navy950,
    primaryContainer = TaxiColors.Accent100,
    onPrimaryContainer = TaxiColors.Navy950,
    secondary = TaxiColors.Navy900,
    onSecondary = TaxiColors.Surface0,
    secondaryContainer = TaxiColors.Accent100,
    onSecondaryContainer = TaxiColors.Navy900,
    tertiary = TaxiColors.Info600,
    onTertiary = TaxiColors.Surface0,
    tertiaryContainer = TaxiColors.Info100,
    onTertiaryContainer = TaxiColors.Ink900,
    error = TaxiColors.Danger600,
    onError = TaxiColors.Surface0,
    errorContainer = TaxiColors.Danger100,
    onErrorContainer = TaxiColors.Danger600,
    background = TaxiColors.Surface1,
    onBackground = TaxiColors.Ink900,
    surface = TaxiColors.Surface0,
    onSurface = TaxiColors.Ink900,
    surfaceVariant = TaxiColors.Surface2,
    onSurfaceVariant = TaxiColors.Ink700,
    outline = TaxiColors.StrokeStrong,
    outlineVariant = TaxiColors.StrokeSubtle,
    scrim = TaxiColors.Scrim,
)
