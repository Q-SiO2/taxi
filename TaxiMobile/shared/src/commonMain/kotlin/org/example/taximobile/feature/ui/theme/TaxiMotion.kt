package org.example.taximobile.feature.ui.theme

import androidx.compose.animation.core.CubicBezierEasing

/** Shared durations and easing; reduced-motion policy is applied by each motion-bearing component. */
object TaxiMotion {
    const val InstantMillis = 0
    const val FastMillis = 120
    const val StandardMillis = 220
    const val EmphasizedMillis = 320
    const val InformationalBannerMillis = 4_000

    val StandardEasing = CubicBezierEasing(0.2f, 0f, 0f, 1f)
    val ExitEasing = CubicBezierEasing(0.4f, 0f, 1f, 1f)
}
