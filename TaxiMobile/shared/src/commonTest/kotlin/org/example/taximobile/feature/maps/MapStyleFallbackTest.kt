package org.example.taximobile.feature.maps

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class MapStyleFallbackTest {
    @Test
    fun fallback_style_has_no_remote_asset_dependencies() {
        assertTrue(TaxiMobileFallbackMapStyleJson.contains("taximobile-neutral-background"))
        assertFalse(TaxiMobileFallbackMapStyleJson.contains("http://"))
        assertFalse(TaxiMobileFallbackMapStyleJson.contains("https://"))
        assertFalse(TaxiMobileFallbackMapStyleJson.contains("sprite"))
        assertFalse(TaxiMobileFallbackMapStyleJson.contains("glyphs"))
    }
}
