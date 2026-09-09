package org.example.taximobile.operations.model

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlinx.serialization.json.Json

class AccountSecurityModelsTest {
    @Test
    fun permission_exposes_only_the_account_security_destination() {
        assertEquals(
            listOf(OperationsDestination.ACCOUNT_SECURITY),
            availableDestinations(setOf(MANAGE_ACCOUNT_SECURITY)),
        )
    }

    @Test
    fun command_requires_market_uuid_case_and_exact_confirmation() {
        val valid = accountSecurityInputError(
            marketId = "7f5b1477-0773-4a3c-80ef-ae7a4db56fa7",
            targetUserId = "eef3fa3a-5740-4b47-a22b-b4638a0870fa",
            action = AccountSecurityAction.SUSPEND,
            reasonCode = "ACCOUNT_COMPROMISE",
            caseReference = "sec-case-2026",
            confirmation = "suspend",
        )
        assertNull(valid)
        assertTrue(
            accountSecurityInputError(
                marketId = null,
                targetUserId = "not-a-user",
                action = AccountSecurityAction.SUSPEND,
                reasonCode = "FREE_TEXT",
                caseReference = "called us",
                confirmation = "yes",
            )!!.contains("market", ignoreCase = true)
        )
    }

    @Test
    fun response_decodes_revocation_counts() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<AccountSecurityActionResponse>(
            """{"user_id":"eef3fa3a-5740-4b47-a22b-b4638a0870fa","status":"SUSPENDED","sessions_revoked":3,"device_registrations_revoked":2,"changed_at":"2026-09-01T20:00:00Z"}"""
        )
        assertEquals(3, response.sessionsRevoked)
        assertEquals(2, response.deviceRegistrationsRevoked)
    }
}
