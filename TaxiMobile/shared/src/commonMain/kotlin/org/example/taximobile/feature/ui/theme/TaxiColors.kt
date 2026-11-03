package org.example.taximobile.feature.ui.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

/** Semantic presentation values. Legacy tone names remain aliases during the view rollout. */
open class TaxiPalette(
    val page: Color, val surface: Color, val ink: Color, val secondaryInk: Color,
    val action: Color, val selection: Color, val stroke: Color,
    val quiet: Boolean = false,
) {
    val Navy950 = ink
    val Navy900 = ink
    val Navy800 = ink
    val Navy700 = secondaryInk
    val Navy600 = secondaryInk
    val Navy500 = secondaryInk
    val Navy400 = stroke
    val Navy300 = if (quiet) Color(0xFFCCCCCC) else Color(0xFFCFCCD8)
    val Navy200 = selection
    val Navy100 = selection
    val Navy50 = page
    val Accent600 = action
    val Accent500 = action
    val Accent400 = if (quiet) Color(0xFFCCCCCC) else Color(0xFFFFD45C)
    val Accent100 = selection
    val Success600 = if (quiet) Color(0xFF333333) else Color(0xFF12653D)
    val Success100 = if (quiet) Color(0xFFECECEC) else Color(0xFFDDF5E8)
    val Warning600 = if (quiet) Color(0xFF424242) else Color(0xFF785000)
    val Warning100 = if (quiet) Color(0xFFF0F0F0) else Color(0xFFFFF3D6)
    val Danger600 = if (quiet) Color(0xFF202020) else Color(0xFFAF2525)
    val Danger100 = if (quiet) Color(0xFFE4E4E4) else Color(0xFFFDE8E8)
    val Info600 = if (quiet) Color(0xFF383838) else Color(0xFF254F99)
    val Info100 = if (quiet) Color(0xFFEEEEEE) else Color(0xFFE6F0FA)
    val Surface0 = surface
    val Surface1 = page
    val Surface2 = selection
    val Ink900 = ink
    val Ink700 = secondaryInk
    val Ink500 = secondaryInk
    val Ink300 = stroke
    val StrokeSubtle = stroke.copy(alpha = 0.42f)
    val StrokeStrong = stroke
    val Scrim = ink.copy(alpha = 0.40f)
    val MapOverlay = ink.copy(alpha = 0.12f)
}

fun taxiPalette(style: TaxiStyle): TaxiPalette = when (style) {
    TaxiStyle.FoldedStreets -> TaxiPalette(Color(0xFFF7EFD9), Color(0xFFFFFDF4), Color(0xFF191A23), Color(0xFF52525C), Color(0xFF263AD4), Color(0xFFE8E8FF), Color(0xFF656571))
    TaxiStyle.StreetPress -> TaxiPalette(Color(0xFFFFF8E8), Color(0xFFFFF8E8), Color(0xFF191A23), Color(0xFF4B4B4B), Color(0xFF191A23), Color(0xFFFFF3B5), Color(0xFF5C5C5C))
    TaxiStyle.GlazedMachine -> TaxiPalette(Color(0xFFF7F0E5), Color(0xFFFFFDF5), Color(0xFF191A23), Color(0xFF565463), Color(0xFF31317D), Color(0xFFEEE6D9), Color(0xFF656277))
    TaxiStyle.Notepad -> TaxiPalette(Color(0xFFF5F5F5), Color.White, Color(0xFF181818), Color(0xFF505050), Color(0xFF202020), Color(0xFFECECEC), Color(0xFF737373), quiet = true)
}

/** Default tokens for pure helpers; UI reads TaxiTheme.colors from composition. */
object TaxiColors : TaxiPalette(Color(0xFFF7EFD9), Color(0xFFFFFDF4), Color(0xFF191A23), Color(0xFF52525C), Color(0xFF263AD4), Color(0xFFE8E8FF), Color(0xFF656571))

internal fun taxiLightColorScheme(colors: TaxiPalette = TaxiColors): ColorScheme = lightColorScheme(
    primary = colors.action, onPrimary = Color.White,
    primaryContainer = colors.selection, onPrimaryContainer = colors.ink,
    secondary = colors.ink, onSecondary = Color.White,
    secondaryContainer = colors.selection, onSecondaryContainer = colors.ink,
    tertiary = colors.Info600, onTertiary = Color.White,
    tertiaryContainer = colors.Info100, onTertiaryContainer = colors.ink,
    error = colors.Danger600, onError = Color.White,
    errorContainer = colors.Danger100, onErrorContainer = colors.Danger600,
    background = colors.page, onBackground = colors.ink,
    surface = colors.surface, onSurface = colors.ink,
    surfaceVariant = colors.selection, onSurfaceVariant = colors.secondaryInk,
    // Material dialogs, menus and elevated controls read these newer roles.
    // Leaving them at library defaults leaks lavender into Notepad.
    surfaceDim = colors.page, surfaceBright = colors.surface,
    surfaceContainerLowest = colors.surface, surfaceContainerLow = colors.page,
    surfaceContainer = colors.selection, surfaceContainerHigh = colors.selection,
    surfaceContainerHighest = colors.selection, surfaceTint = colors.action,
    inverseSurface = colors.ink, inverseOnSurface = colors.surface,
    inversePrimary = colors.selection,
    outline = colors.stroke, outlineVariant = colors.StrokeSubtle, scrim = colors.Scrim,
)
