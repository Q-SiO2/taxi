@file:OptIn(kotlin.js.ExperimentalWasmJsInterop::class)

package org.example.taximobile.applicant.state

import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.coroutines.suspendCoroutine
import kotlin.io.encoding.Base64
import kotlinx.browser.document
import org.example.taximobile.domain.drivers.DriverDocumentUpload
import org.w3c.dom.HTMLInputElement
import org.w3c.files.FileReader

internal actual val browserDriverDocumentPickerAvailable: Boolean = true

internal actual suspend fun pickBrowserDriverDocument(): DriverDocumentUpload? =
    suspendCoroutine { continuation ->
        val input = document.createElement("input") as HTMLInputElement
        input.type = "file"
        input.accept = ALLOWED_MEDIA_TYPES.joinToString(",")
        input.style.display = "none"
        document.body?.appendChild(input)
        var completed = false

        fun finish(upload: DriverDocumentUpload?) {
            if (completed) return
            completed = true
            input.remove()
            continuation.resume(upload)
        }

        fun fail(message: String) {
            if (completed) return
            completed = true
            input.remove()
            continuation.resumeWithException(IllegalArgumentException(message))
        }

        input.onchange = {
            val file = input.files?.item(0)
            when {
                file == null -> finish(null)
                file.size.toDouble() < 1.0 || file.size.toDouble() > MAX_BYTES.toDouble() ->
                    fail("Document must be between 1 byte and 10 MB.")
                file.type !in ALLOWED_MEDIA_TYPES ->
                    fail("Choose a PDF, JPEG, or PNG file.")
                else -> {
                    val reader = FileReader()
                    reader.onerror = {
                        fail("Document could not be read.")
                    }
                    reader.onload = {
                        val data = reader.result?.toString().orEmpty()
                        val separator = data.indexOf(',')
                        if (separator < 0) {
                            fail("Document could not be read.")
                        } else {
                            val bytes = runCatching {
                                Base64.decode(data.substring(separator + 1))
                            }.getOrNull()
                            if (bytes == null || bytes.isEmpty() || bytes.size > MAX_BYTES) {
                                fail("Document could not be read.")
                            } else {
                                finish(
                                    DriverDocumentUpload(
                                        fileName = file.name.replace("\u0000", ""),
                                        mediaType = file.type,
                                        bytes = bytes,
                                    ),
                                )
                            }
                        }
                    }
                    reader.readAsDataURL(file)
                }
            }
        }
        input.addEventListener("cancel", { finish(null) })
        input.click()
    }

private const val MAX_BYTES = 10 * 1024 * 1024
private val ALLOWED_MEDIA_TYPES = setOf("application/pdf", "image/jpeg", "image/png")
