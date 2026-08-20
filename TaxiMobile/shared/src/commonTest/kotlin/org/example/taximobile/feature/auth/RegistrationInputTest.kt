package org.example.taximobile.feature.auth

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class RegistrationInputTest {
    @Test
    fun `valid email or common Moroccan phone spellings enable registration`() {
        assertTrue(registrationInputValidity("Passenger", "user@example.ma", "", "a-long-password").canSubmit)
        assertTrue(registrationInputValidity("Passenger", "", "06 00 00 00 00", "a-long-password").canSubmit)
        assertTrue(registrationInputValidity("Passenger", "", "+212600000000", "a-long-password").canSubmit)
        assertTrue(registrationInputValidity("Passenger", "", "00212600000000", "a-long-password").canSubmit)
    }

    @Test
    fun `invalid supplied contact or short password prevents registration`() {
        assertFalse(registrationInputValidity("Passenger", "not-an-email", "", "a-long-password").canSubmit)
        assertFalse(registrationInputValidity("Passenger", "", "+33123456789", "a-long-password").canSubmit)
        assertFalse(registrationInputValidity("Passenger", "user@example.ma", "", "short").canSubmit)
        assertFalse(registrationInputValidity("Passenger", "", "", "a-long-password").canSubmit)
    }

    @Test
    fun `one malformed supplied contact is not hidden by another valid contact`() {
        val validity = registrationInputValidity(
            "Passenger",
            "user@example.ma",
            "+33123456789",
            "a-long-password",
        )

        assertTrue(validity.emailValid)
        assertFalse(validity.phoneNumberValid)
        assertFalse(validity.canSubmit)
    }
}
