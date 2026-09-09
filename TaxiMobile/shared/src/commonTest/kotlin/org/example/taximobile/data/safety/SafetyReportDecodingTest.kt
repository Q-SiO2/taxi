package org.example.taximobile.data.safety

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import org.example.taximobile.domain.safety.SafetyCategory

class SafetyReportDecodingTest {
    @Test
    fun `participant report decoding keeps only safe status projection`() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<SafetyReportListResponse>(
            """{
              "items": [{
                "id": "report-1",
                "ride_id": "ride-1",
                "category": "UNSAFE_DRIVING",
                "status": "ACKNOWLEDGED",
                "latest_public_message": "A safety specialist is reviewing your report.",
                "created_at": "2026-08-24T12:00:00Z",
                "updated_at": "2026-08-24T12:05:00Z",
                "internal_notes": "must be ignored",
                "reported_user_id": "must-not-enter-domain"
              }],
              "page": 1,
              "limit": 20,
              "total": 1
            }"""
        )

        val report = response.items.single().toDomain()
        assertEquals(SafetyCategory.UNSAFE_DRIVING, report.category)
        assertEquals("ACKNOWLEDGED", report.status)
        assertEquals("A safety specialist is reviewing your report.", report.latestPublicMessage)
        assertEquals("2026-08-24T12:05:00Z", report.updatedAt)
    }

    @Test
    fun `future safety category degrades to explicit unknown value`() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<SafetyReportListResponse>(
            """{
              "items": [{
                "id": "report-2",
                "ride_id": "ride-2",
                "category": "FUTURE_SERVER_CATEGORY",
                "status": "SUBMITTED",
                "created_at": "2026-08-24T12:00:00Z"
              }],
              "page": 1,
              "limit": 20,
              "total": 1
            }"""
        )

        assertEquals(SafetyCategory.UNKNOWN, response.items.single().toDomain().category)
    }
}
