package org.example.taximobile.applicant.state

import kotlin.io.encoding.Base64
import kotlin.js.Promise
import kotlinx.browser.document
import kotlinx.coroutines.await
import org.example.taximobile.domain.drivers.DriverDocumentUpload
import org.w3c.dom.HTMLInputElement
import org.w3c.files.FileReader

internal actual val browserDriverDocumentPickerAvailable: Boolean = true

private fun chooseBrowserDocument(maxBytes: Int): Promise<String?> = Promise { resolve, reject ->
    val input = document.createElement("input") as HTMLInputElement
    input.type = "file"
    input.accept = ALLOWED_MEDIA_TYPES.joinToString(",")
    input.style.display = "none"
    document.body?.appendChild(input)

    fun cleanup() = input.remove()

    input.onchange = {
        val file = input.files?.item(0)
        when {
            file == null -> {
                cleanup()
                resolve(null)
            }
            file.size.toDouble() < 1.0 || file.size.toDouble() > maxBytes.toDouble() -> {
                cleanup()
                reject(Throwable("Document must be between 1 byte and 10 MB."))
            }
            file.type !in ALLOWED_MEDIA_TYPES -> {
                cleanup()
                reject(Throwable("Choose a PDF, JPEG, or PNG file."))
            }
            else -> {
                val reader = FileReader()
                reader.onerror = {
                    cleanup()
                    reject(Throwable("Document could not be read."))
                }
                reader.onload = {
                    val data = reader.result?.toString().orEmpty()
                    val separator = data.indexOf(',')
                    cleanup()
                    if (separator < 0) {
                        reject(Throwable("Document could not be read."))
                    } else {
                        resolve(
                            file.name.replace("\u0000", "") +
                                '\u0000' + file.type + '\u0000' + data.substring(separator + 1),
                        )
                    }
                }
                reader.readAsDataURL(file)
            }
        }
        null
    }
    input.click()
}

internal actual suspend fun pickBrowserDriverDocument(): DriverDocumentUpload? {
    val payload = chooseBrowserDocument(MAX_BYTES).await() ?: return null
    val parts = payload.split('\u0000', limit = 3)
    require(parts.size == 3) { "The selected document response was invalid." }
    return DriverDocumentUpload(
        fileName = parts[0],
        mediaType = parts[1],
        bytes = Base64.decode(parts[2]),
    )
}

private const val MAX_BYTES = 10 * 1024 * 1024
private val ALLOWED_MEDIA_TYPES = setOf("application/pdf", "image/jpeg", "image/png")
