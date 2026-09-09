package org.example.taximobile.applicant.state

import org.example.taximobile.domain.drivers.DriverDocumentUpload

internal expect val browserDriverDocumentPickerAvailable: Boolean

internal expect suspend fun pickBrowserDriverDocument(): DriverDocumentUpload?
