package org.example.taximobile.feature.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertTopPositionInRootIsEqualTo
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.driver.onboarding.DriverOnboardingScreen
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import kotlin.test.Test

@OptIn(ExperimentalTestApi::class)
class DriverOnboardingInsetsUiTest {
    @Test
    fun recruiting_header_clears_system_insets_without_changing_existing_content_spacing() = runComposeUiTest {
        setContent {
            Box(Modifier.size(360.dp, 760.dp)) {
                DriverOnboardingScreen(
                    state = AppUiState.DriverOnboarding("Synthetic applicant", emptyList(), emptyList()),
                    pendingAction = null,
                    onRefresh = {},
                    onLogout = {},
                    onCreateApplication = { _, _ -> },
                    onSelectApplication = { _, _ -> },
                    onSaveApplication = { _, _, _, _, _, _, _ -> },
                    onSubmitApplication = { _, _ -> },
                    onWithdrawApplication = { _, _ -> },
                    documentPickerAvailable = false,
                    onUploadDocument = { _, _, _, _ -> },
                    onDeleteDocument = { _, _, _, _ -> },
                    onRegisterVehicle = { _, _ -> },
                    safeInsets = WindowInsets(top = 48.dp, bottom = 24.dp),
                )
            }
        }
        onNodeWithText("Become a TaxiMobile driver")
            .assertTopPositionInRootIsEqualTo(48.dp + TaxiSpacing.Lg)
    }
}
