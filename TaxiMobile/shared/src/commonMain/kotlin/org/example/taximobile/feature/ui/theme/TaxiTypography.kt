package org.example.taximobile.feature.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import org.jetbrains.compose.resources.Font
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.ibm_plex_mono_medium
import taximobile.shared.generated.resources.manrope_variable
import taximobile.shared.generated.resources.sora_variable

data class TaxiAdditionalTypography(
    val monoMedium: TextStyle,
    val monoSmall: TextStyle,
)

@Composable
internal fun taxiTypography(): Pair<Typography, TaxiAdditionalTypography> {
    val sora = FontFamily(
        Font(Res.font.sora_variable, FontWeight.SemiBold),
        Font(Res.font.sora_variable, FontWeight.Bold),
    )
    val manrope = FontFamily(
        Font(Res.font.manrope_variable, FontWeight.Normal),
        Font(Res.font.manrope_variable, FontWeight.Medium),
        Font(Res.font.manrope_variable, FontWeight.SemiBold),
        Font(Res.font.manrope_variable, FontWeight.Bold),
    )
    val mono = FontFamily(Font(Res.font.ibm_plex_mono_medium, FontWeight.Medium))

    val typography = Typography(
        displayLarge = TextStyle(fontFamily = sora, fontWeight = FontWeight.Bold, fontSize = 40.sp, lineHeight = 44.sp, letterSpacing = (-0.4).sp),
        displayMedium = TextStyle(fontFamily = sora, fontWeight = FontWeight.Bold, fontSize = 32.sp, lineHeight = 36.sp, letterSpacing = (-0.16).sp),
        displaySmall = TextStyle(fontFamily = sora, fontWeight = FontWeight.SemiBold, fontSize = 24.sp, lineHeight = 28.sp),
        titleLarge = TextStyle(fontFamily = manrope, fontWeight = FontWeight.Bold, fontSize = 20.sp, lineHeight = 26.sp),
        titleMedium = TextStyle(fontFamily = manrope, fontWeight = FontWeight.SemiBold, fontSize = 18.sp, lineHeight = 24.sp),
        titleSmall = TextStyle(fontFamily = manrope, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 22.sp),
        bodyLarge = TextStyle(fontFamily = manrope, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 24.sp),
        bodyMedium = TextStyle(fontFamily = manrope, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 20.sp),
        bodySmall = TextStyle(fontFamily = manrope, fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.12.sp),
        labelLarge = TextStyle(fontFamily = manrope, fontWeight = FontWeight.Bold, fontSize = 14.sp, lineHeight = 18.sp, letterSpacing = 0.28.sp),
        labelMedium = TextStyle(fontFamily = manrope, fontWeight = FontWeight.SemiBold, fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.36.sp),
    )
    return typography to TaxiAdditionalTypography(
        monoMedium = TextStyle(fontFamily = mono, fontWeight = FontWeight.Medium, fontSize = 14.sp, lineHeight = 18.sp),
        monoSmall = TextStyle(fontFamily = mono, fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 16.sp),
    )
}
