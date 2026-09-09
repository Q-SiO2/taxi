package org.example.taximobile.operations.state

import kotlin.io.encoding.Base64
import kotlinx.browser.document
import org.example.taximobile.operations.data.ProtectedDriverDocumentDownload
import org.w3c.dom.HTMLAnchorElement

internal actual val browserProtectedDocumentDownloadAvailable: Boolean = true

internal actual fun saveProtectedDocumentDownload(download: ProtectedDriverDocumentDownload) {
    val anchor = document.createElement("a") as HTMLAnchorElement
    anchor.href = "data:${download.mediaType};base64,${Base64.encode(download.bytes)}"
    anchor.download = download.fileName
    anchor.rel = "noopener"
    anchor.style.display = "none"
    document.body?.appendChild(anchor)
    anchor.click()
    anchor.remove()
}
