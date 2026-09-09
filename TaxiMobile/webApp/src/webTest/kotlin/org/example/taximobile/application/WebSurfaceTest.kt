package org.example.taximobile.application

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
            "Provide an email address or Moroccan phone number.",
            validateApplicantRegistration("Applicant", "", "", "long-password"),
        )
        assertEquals(
            "Use a password between 12 and 256 characters.",
            validateApplicantRegistration("Applicant", "driver@example.test", "", "short"),
        )
        assertEquals(null, validateApplicantRegistration("Applicant", "driver@example.test", "", "long-password"))
        assertEquals("Enter your password.", validateApplicantLogin("driver@example.test", ""))
    }
}
