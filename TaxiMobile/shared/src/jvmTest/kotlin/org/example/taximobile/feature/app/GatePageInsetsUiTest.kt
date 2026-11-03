package org.example.taximobile.feature.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertTopPositionInRootIsEqualTo
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.dp
import org.example.taximobile.app.AppRole
import kotlin.test.Test

@OptIn(ExperimentalTestApi::class)
class GatePageInsetsUiTest {
    @Test
    fun signed_out_header_starts_after_safe_insets_and_existing_content_padding() = runComposeUiTest {
        setContent {
            Box(Modifier.size(300.dp, 500.dp)) {
                GatePage(AppRole.PASSENGER, safeInsets = WindowInsets(top = 48.dp, bottom = 24.dp)) {
                    Text("Account content")
                }
            }
        }
        onNodeWithText("TaxiMobile").assertTopPositionInRootIsEqualTo(72.dp)
    }
}
