package org.example.taximobile.feature.ui.components

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.painter.BitmapPainter
import androidx.compose.ui.graphics.painter.Painter
import kotlinx.coroutines.CancellationException
import org.jetbrains.compose.resources.decodeToImageBitmap
import taximobile.shared.generated.resources.Res

/** Approved decorative, locally bundled PNGs only; never operational data. */
internal enum class BundledArtwork(val resourcePath: String, val maxBytes: Int = 1_048_576) {
    Landing("drawable/illustration_landing_runtime.png", maxBytes = 2_097_152),
    BrandMark("drawable/brand_logo_mark_runtime.png"),
    VehicleSilhouette("drawable/vehicle_silhouette_standard_runtime.png"),
}

private const val MAX_ARTWORK_BYTES = 1_048_576
private val PNG_SIGNATURE = byteArrayOf(-119, 80, 78, 71, 13, 10, 26, 10)

/**
 * Optional artwork may fall back; authentication, maps, documents and other
 * authoritative/operational resources must never use this failure policy.
 * Read/decode errors are contained outside composition, where painterResource
 * would otherwise throw and close the screen. Cancellation and fatal VM errors
 * are deliberately not converted into an artwork fallback.
 */
internal suspend fun <T> loadOptionalRaster(
    readBytes: suspend () -> ByteArray,
    maxBytes: Int = MAX_ARTWORK_BYTES,
    decode: suspend (ByteArray) -> T,
): T? = try {
    val bytes = readBytes()
    if (maxBytes !in PNG_SIGNATURE.size..2_097_152 ||
        bytes.size !in PNG_SIGNATURE.size..maxBytes ||
        !bytes.copyOfRange(0, PNG_SIGNATURE.size).contentEquals(PNG_SIGNATURE)
    ) {
        null
    } else {
        decode(bytes)
    }
} catch (cancelled: CancellationException) {
    throw cancelled
} catch (_: Exception) {
    // A missing/corrupt optional image leaves the documented accessible fallback.
    null
}

@Composable
internal fun rememberOptionalArtworkPainter(
    artwork: BundledArtwork,
    enabled: Boolean,
): Painter? {
    val bitmap by produceState<ImageBitmap?>(null, artwork, enabled) {
        value = null
        if (enabled) {
            value = loadOptionalRaster(
                readBytes = { Res.readBytes(artwork.resourcePath) },
                maxBytes = artwork.maxBytes,
                decode = { it.decodeToImageBitmap() },
            )
        }
    }
    // Disabling an asset takes effect immediately, not after the effect runs.
    val visibleBitmap = if (enabled) bitmap else null
    return visibleBitmap?.let { remember(it) { BitmapPainter(it) } }
}
