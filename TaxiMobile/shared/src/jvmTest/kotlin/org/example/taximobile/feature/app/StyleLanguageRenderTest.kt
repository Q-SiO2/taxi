package org.example.taximobile.feature.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asSkiaBitmap
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.dp
import org.example.taximobile.App
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.example.taximobile.feature.ui.theme.TaxiStylePreferences
import org.example.taximobile.feature.ui.theme.TaxiStyleStore
import org.jetbrains.skia.EncodedImageFormat
import org.jetbrains.skia.Image
import java.nio.file.Files
import java.nio.file.Path
import java.util.Locale
import kotlin.test.Test
import kotlin.test.assertTrue

@OptIn(ExperimentalTestApi::class)
class StyleLanguageRenderTest {
    @Test
    fun every_style_renders_the_translated_welcome_and_retains_reachable_actions() {
        val original = Locale.getDefault()
        try {
            for ((language, title, action) in listOf(
                Triple("en", "Your city. Your taxi.", "Sign in"),
                Triple("fr", "Votre ville. Votre taxi.", "Se connecter"),
                Triple("ar", "مدينتك. سيارة أجرتك.", "تسجيل الدخول"),
            )) {
                for (style in TaxiStyle.entries) {
                    Locale.setDefault(Locale.forLanguageTag(language))
                    val preferences = TaxiStylePreferences(object : TaxiStyleStore {
                        override fun read() = style.storageValue
                        override fun write(value: String) = Unit
                    })
                    runComposeUiTest {
                        setContent {
                            Box(Modifier.size(360.dp, 800.dp)) {
                                App(stylePreferences = preferences, state = AppUiState.SignedOut())
                            }
                        }
                        onNodeWithText(title).assertIsDisplayed()
                        onNodeWithTag("identity-frame-${style.storageValue}").assertIsDisplayed()
                        onNodeWithText(action).performScrollTo().assertIsDisplayed()
                        System.getenv("TAXIMOBILE_STYLE_EVIDENCE_DIR")?.let { directory ->
                            val path = Path.of(directory)
                            Files.createDirectories(path)
                            val data = Image.makeFromBitmap(onRoot().captureToImage().asSkiaBitmap())
                                .encodeToData(EncodedImageFormat.PNG)
                            assertTrue(data != null)
                            Files.write(path.resolve("${style.storageValue}-$language.png"), data.bytes)
                        }
                    }
                }
            }
        } finally { Locale.setDefault(original) }
    }
}
