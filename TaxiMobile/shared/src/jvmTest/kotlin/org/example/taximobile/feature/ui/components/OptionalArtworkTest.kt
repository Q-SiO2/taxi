package org.example.taximobile.feature.ui.components

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import org.jetbrains.compose.resources.decodeToImageBitmap
import taximobile.shared.generated.resources.Res
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull
import kotlin.test.assertNotNull

class OptionalArtworkTest {
    private val signature = byteArrayOf(-119, 80, 78, 71, 13, 10, 26, 10)

    @Test
    fun every_bundled_artwork_decodes_on_jvm() = runBlocking {
        val dimensions = mapOf(
            BundledArtwork.Landing to (941 to 1672),
            BundledArtwork.BrandMark to (256 to 256),
            BundledArtwork.VehicleSilhouette to (640 to 360),
        )
        for ((artwork, expected) in dimensions) {
            val bitmap = assertNotNull(loadOptionalRaster({ Res.readBytes(artwork.resourcePath) }, maxBytes = artwork.maxBytes) { it.decodeToImageBitmap() })
            assertEquals(expected.first, bitmap.width)
            assertEquals(expected.second, bitmap.height)
        }
    }

    @Test
    fun valid_png_reaches_decoder() = runBlocking {
        assertEquals("decoded", loadOptionalRaster({ signature }) { "decoded" })
    }

    @Test
    fun portrait_has_an_explicit_budget_without_expanding_other_assets() = runBlocking {
        val bytes = ByteArray(1_048_577).also { signature.copyInto(it) }
        assertNull(loadOptionalRaster<String>({ bytes }) { "decoded" })
        assertEquals("decoded", loadOptionalRaster({ bytes }, maxBytes = BundledArtwork.Landing.maxBytes) { "decoded" })
        assertNull(loadOptionalRaster<String>({ bytes }, maxBytes = 2_097_153) { "decoded" })
        assertEquals(1_048_576, BundledArtwork.BrandMark.maxBytes)
    }

    @Test
    fun missing_artwork_uses_fallback_without_decoding() = runBlocking {
        assertNull(loadOptionalRaster<String>({ error("Missing decorative resource") }) { error("Unexpected decode") })
    }

    @Test
    fun corrupt_png_uses_fallback() = runBlocking {
        assertNull(loadOptionalRaster<String>({ signature }) { error("Invalid PNG payload") })
    }

    @Test
    fun svg_empty_short_and_oversized_inputs_never_reach_decoder() = runBlocking {
        for (bytes in listOf("<svg/>".encodeToByteArray(), byteArrayOf(), signature.take(7).toByteArray(), ByteArray(1_048_577))) {
            assertNull(loadOptionalRaster<String>({ bytes }) { error("Unexpected decode") })
        }
    }

    @Test
    fun cancelled_read_propagates(): Unit = runBlocking {
        assertFailsWith<CancellationException> {
            loadOptionalRaster<String>({ throw CancellationException("Cancelled") }) { "decoded" }
        }
    }

    @Test
    fun cancelled_decode_propagates(): Unit = runBlocking {
        assertFailsWith<CancellationException> {
            loadOptionalRaster<String>({ signature }) { throw CancellationException("Cancelled") }
        }
    }

    @Test
    fun fatal_errors_are_not_hidden_as_decoration_failures(): Unit = runBlocking {
        assertFailsWith<LinkageError> {
            loadOptionalRaster<String>({ throw LinkageError("Broken runtime") }) { "decoded" }
        }
    }
}
