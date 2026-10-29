package org.example.taximobile.application

import kotlin.test.Test
import kotlin.test.assertEquals
import org.example.taximobile.applicant.state.applicantFailureMessage
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.feature.ui.text.UiMessage
import org.example.taximobile.operations.data.OperationsApiException
import org.example.taximobile.operations.state.toMessage
import taximobile.shared.generated.resources.*

class WebFailurePresentationTest {
    @Test
    fun `catalog outage is not reported as rejected document storage`() {
        val error = ApiRequestException(503, "Private transport diagnostic")
        val catalog = applicantFailureMessage(error, publicCatalog = true)
        val command = applicantFailureMessage(error, publicCatalog = false)
        assertEquals(UiMessage(Res.string.web_catalog_unavailable), catalog.localizedDetail)
        assertEquals(UiMessage(Res.string.web_service_unavailable), command.localizedDetail)
        assertEquals("", catalog.detail)
        assertEquals("", command.detail)
    }

    @Test
    fun `unknown command failure preserves uncertainty and suppresses protected diagnostics`() {
        val message = applicantFailureMessage(ApiRequestException(500, "Private record payload"), publicCatalog = false)
        assertEquals(UiMessage(Res.string.web_request_unconfirmed), message.localizedDetail)
        assertEquals("", message.detail)
    }

    @Test
    fun `operations denial and conflict preserve recovery without raw server copy`() {
        val denied = OperationsApiException(403, "Private scope diagnostic").toMessage()
        val conflict = OperationsApiException(409, "Private state diagnostic").toMessage()
        assertEquals(UiMessage(Res.string.web_scope_denied), denied.localizedDetail)
        assertEquals(UiMessage(Res.string.web_record_changed), conflict.localizedDetail)
        assertEquals("", denied.detail)
        assertEquals("", conflict.detail)
    }

    @Test
    fun `authentication rejection differs from a rejected existing session`() {
        val failure = OperationsApiException(401, "Private auth diagnostic")
        assertEquals(UiMessage(Res.string.web_auth_rejected_detail), failure.toMessage(signIn = true).localizedDetail)
        assertEquals(UiMessage(Res.string.web_session_detail), failure.toMessage().localizedDetail)
    }
}
