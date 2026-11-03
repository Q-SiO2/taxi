package org.example.taximobile.operations.model

import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.jsonObject
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class OperatorMembershipModelsTest {
    @Test
    fun `complete edits preserve explicit clearing and concurrency token on the actual wire encoder`() {
        val payload = OperatorMembershipUpdateRequest("SUSPENDED", null, null, null, "2026-10-23T10:00:00Z", "Reviewed roster")
        val encoded = operatorMembershipWireJson.parseToJsonElement(operatorMembershipWireJson.encodeToString(payload)).jsonObject
        for (key in listOf("membership_number", "joined_at", "ended_at")) assertEquals(JsonNull, encoded[key])
        assertEquals("\"2026-10-23T10:00:00Z\"", encoded["expected_updated_at"].toString())
        assertFalse("driver_id" in encoded)
    }

    @Test
    fun `membership dates require offsets and preserve half open end boundary records`() {
        assertTrue(validMembershipDates("", ""))
        assertTrue(validMembershipDates("2026-10-23T12:00:00Z", "2026-10-23T13:00:00+01:00"))
        assertFalse(validMembershipDates("2026-10-23T12:00:00", ""))
        assertFalse(validMembershipDates("2026-10-23T12:00:00Z", "2026-10-23T11:59:59Z"))
        assertFalse(validMembershipDates("", "invalid"))
    }

    @Test
    fun `policy reads preserve old open records and new closed shop records`() {
        val legacy = """{"id":"op","market_id":"ma","name":"Union","operator_type":"COOPERATIVE","status":"ACTIVE","created_at":"date","updated_at":"date"}"""
        val json = Json { ignoreUnknownKeys = true }
        assertFalse(json.decodeFromString<OperatorRecord>(legacy).requiresActiveMembership)
        assertTrue(json.decodeFromString<OperatorRecord>(legacy.dropLast(1)+",\"requires_active_membership\":true}").requiresActiveMembership)
        assertEquals("{\"requires_active_membership\":false}", operatorMembershipWireJson.encodeToString(OperatorMembershipPolicyRequest(false)))
    }

    @Test
    fun `driver IDs cannot accidentally submit a short display reference`() {
        assertFalse(validMembershipDriverId("1234abcd"))
        assertFalse(validMembershipDriverId("00000000-0000-0000-0000-00000000000g"))
        assertTrue(validMembershipDriverId("00000000-0000-0000-0000-000000000001"))
    }
}
