package org.example.taximobile.feature.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.intl.Locale
import androidx.compose.ui.unit.sp
import org.jetbrains.compose.resources.Font
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.ibm_plex_mono_medium
import taximobile.shared.generated.resources.ibmplexsans
import taximobile.shared.generated.resources.plusjakartasans
import taximobile.shared.generated.resources.ibmplexsansarabic
import taximobile.shared.generated.resources.ibmplexsansarabic_500
import taximobile.shared.generated.resources.ibmplexsansarabic_700

data class TaxiAdditionalTypography(
    val monoMedium: TextStyle,
    val monoSmall: TextStyle,
)

@Composable
fun taxiArabicFontFamily(): FontFamily = FontFamily(
    Font(Res.font.ibmplexsansarabic, FontWeight.Normal),
    Font(Res.font.ibmplexsansarabic_500, FontWeight.Medium),
    Font(Res.font.ibmplexsansarabic_700, FontWeight.Bold),
)

@Composable
internal fun taxiTypography(style: TaxiStyle = TaxiStyle.FoldedStreets): Pair<Typography, TaxiAdditionalTypography> {
    val mono = FontFamily(Font(Res.font.ibm_plex_mono_medium, FontWeight.Medium))
    val arabic = taxiArabicFontFamily()
    val usesArabicTypography = Locale.current.language.lowercase() == "ar"
    val identityFont = FontFamily(Font(if (style == TaxiStyle.GlazedMachine) Res.font.plusjakartasans else Res.font.ibmplexsans))
    val displayFamily = if (usesArabicTypography) arabic else identityFont
    val textFamily = if (usesArabicTypography) arabic else identityFont
    val displayLargeSpacing = if (usesArabicTypography) 0.sp else (-0.4).sp
    val displayMediumSpacing = if (usesArabicTypography) 0.sp else (-0.16).sp
    val bodySmallSpacing = if (usesArabicTypography) 0.sp else 0.12.sp
    val labelLargeSpacing = if (usesArabicTypography) 0.sp else 0.28.sp
    val labelMediumSpacing = if (usesArabicTypography) 0.sp else 0.36.sp

    val typography = Typography(
        displayLarge = TextStyle(fontFamily = displayFamily, fontWeight = FontWeight.Bold, fontSize = 40.sp, lineHeight = 48.sp, letterSpacing = displayLargeSpacing),
        displayMedium = TextStyle(fontFamily = displayFamily, fontWeight = FontWeight.Bold, fontSize = 32.sp, lineHeight = 40.sp, letterSpacing = displayMediumSpacing),
        displaySmall = TextStyle(fontFamily = displayFamily, fontWeight = FontWeight.SemiBold, fontSize = 24.sp, lineHeight = 32.sp),
        titleLarge = TextStyle(fontFamily = textFamily, fontWeight = FontWeight.Bold, fontSize = 20.sp, lineHeight = 28.sp),
        titleMedium = TextStyle(fontFamily = textFamily, fontWeight = FontWeight.SemiBold, fontSize = 18.sp, lineHeight = 26.sp),
        titleSmall = TextStyle(fontFamily = textFamily, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 24.sp),
        bodyLarge = TextStyle(fontFamily = textFamily, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 26.sp),
        bodyMedium = TextStyle(fontFamily = textFamily, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 22.sp),
        bodySmall = TextStyle(fontFamily = textFamily, fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 18.sp, letterSpacing = bodySmallSpacing),
        labelLarge = TextStyle(fontFamily = textFamily, fontWeight = FontWeight.Bold, fontSize = 14.sp, lineHeight = 20.sp, letterSpacing = labelLargeSpacing),
        labelMedium = TextStyle(fontFamily = textFamily, fontWeight = FontWeight.SemiBold, fontSize = 12.sp, lineHeight = 18.sp, letterSpacing = labelMediumSpacing),
    )
    return typography to TaxiAdditionalTypography(
        monoMedium = TextStyle(fontFamily = mono, fontWeight = FontWeight.Medium, fontSize = 14.sp, lineHeight = 18.sp),
        monoSmall = TextStyle(fontFamily = mono, fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 16.sp),
    )
}
