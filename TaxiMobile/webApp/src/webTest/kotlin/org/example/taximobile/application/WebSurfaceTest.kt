package org.example.taximobile.application

import org.example.taximobile.feature.ui.text.UiMessage
import taximobile.shared.generated.resources.*
import kotlin.test.Test
import kotlin.test.assertEquals
import org.example.taximobile.applicant.state.validateApplicantLogin
import org.example.taximobile.applicant.state.validateApplicantRegistration

class WebSurfaceTest {
    @Test
    fun `applicant route never boots the operations composition root`() {
        assertEquals(WebSurface.APPLICANT, selectWebSurface("/apply", ""))
        assertEquals(WebSurface.APPLICANT, selectWebSurface("/", "#/apply"))
        assertEquals(WebSurface.OPERATIONS, selectWebSurface("/", ""))
        assertEquals(WebSurface.OPERATIONS, selectWebSurface("/operations", ""))
    }

    @Test
    fun `registration validation matches backend minimum boundaries`() {
        assertEquals(
            UiMessage(Res.string.web_contact_required),
            validateApplicantRegistration("Applicant", "", "", "long-password"),
        )
        assertEquals(
            UiMessage(Res.string.web_password_registration_invalid),
            validateApplicantRegistration("Applicant", "driver@example.test", "", "short"),
        )
        assertEquals(null, validateApplicantRegistration("Applicant", "driver@example.test", "", "long-password"))
        assertEquals(UiMessage(Res.string.web_password_required), validateApplicantLogin("driver@example.test", ""))
    }
}
