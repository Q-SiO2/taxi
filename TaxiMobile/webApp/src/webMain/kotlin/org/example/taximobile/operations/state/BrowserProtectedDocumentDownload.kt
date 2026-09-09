package org.example.taximobile.operations.state

import org.example.taximobile.operations.data.ProtectedDriverDocumentDownload

internal expect val browserProtectedDocumentDownloadAvailable: Boolean

internal expect fun saveProtectedDocumentDownload(download: ProtectedDriverDocumentDownload)
