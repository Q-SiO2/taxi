package org.example.taximobile.data.network

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class ApiFailureTest {
    private val denied = """{"error":{"code":"REQUEST_REJECTED","message":"Active membership with this operator is required.","details":{}}}"""

    @Test
    fun `only the exact admission rejection receives localized product handling`() {
        assertEquals(ApiFailureReason.OPERATOR_MEMBERSHIP_REQUIRED, apiRequestFailure(409, "fallback", denied).reason)
        assertNull(apiRequestFailure(403, "fallback", denied).reason)
        assertNull(apiRequestFailure(500, "fallback", denied).reason)
        assertNull(apiRequestFailure(409, "fallback", denied.replace("REQUEST_REJECTED", "OTHER")).reason)
        assertNull(apiRequestFailure(409, "fallback", denied.replace("is required.", "is required. secret detail")).reason)
    }

    @Test
    fun `untrusted error bodies never become a product message`() {
        for (body in listOf("not-json", "{}", "{\"error\":\"secret\"}", "{\"detail\":\"secret\"}", " ".repeat(4097))) {
            val error = apiRequestFailure(409, "safe fallback", body)
            assertNull(error.reason)
            assertEquals("safe fallback", error.message)
        }
    }
}
