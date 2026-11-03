package org.example.taximobile.feature.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.dp
import org.example.taximobile.App
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.example.taximobile.feature.ui.theme.TaxiStylePreferences
import org.example.taximobile.feature.ui.theme.TaxiStyleStore
import kotlin.test.Test
import kotlin.test.assertEquals

@OptIn(ExperimentalTestApi::class)
class StyleSwitchUiTest {
    @Test
    fun choosing_styles_keeps_the_authentication_draft_and_sends_no_domain_command() = runComposeUiTest {
        val preferences = TaxiStylePreferences(object : TaxiStyleStore {
            var saved: String? = null
            override fun read() = saved
            override fun write(value: String) { saved = value }
        })
        var calls = 0
        setContent {
            Box(Modifier.size(400.dp, 800.dp)) {
                App(stylePreferences = preferences, state = AppUiState.SignedOut(showRegistrationForm = true),
                    onRegister = { _, _, _, _ -> calls++ }, onLogin = { _, _ -> calls++ })
            }
        }
        onNodeWithText("Display name").performScrollTo().performTextInput("Board rehearsal")
        TaxiStyle.entries.forEach { style ->
            onNodeWithTag("style-open").performScrollTo().performClick()
            onNodeWithTag("style-${style.storageValue}").performClick()
            onNodeWithText("Done").performClick()
            onNodeWithText("Display name").assertTextContains("Board rehearsal")
            assertEquals(style, preferences.style)
            assertEquals(0, calls)
        }
    }
}
