package org.example.taximobile.operations.ui

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue
import org.example.taximobile.operations.model.CityAuthorizationAction
import org.example.taximobile.operations.model.RecruitmentLocalizedCopy

class DriverRecruitmentScreenTest {
    @Test
    fun `recruitment presentation covers review and authorization outcomes without guessing unknown codes`() {
        val statuses = listOf("DRAFT", "IN_REVIEW", "ACTIVE", "REPLACED", "NOT_STARTED", "SUBMITTED",
            "UNDER_REVIEW", "ADDITIONAL_INFORMATION_REQUIRED", "APPROVED", "REJECTED", "WITHDRAWN",
            "SUSPENDED", "EXPIRED", "REVOKED", "MISSING", "PRESENT", "PENDING", "ACCEPTED",
            "QUARANTINED", "CLEAN", "ERROR")
        statuses.forEach { assertNotNull(recruitmentCodeResource(it), it) }
        CityAuthorizationAction.entries.forEach { action ->
            assertNotNull(recruitmentCodeResource(action.name))
            action.reasons.forEach { assertNotNull(recruitmentCodeResource(it), it) }
        }
        assertNull(recruitmentCodeResource("FUTURE_SERVER_STATUS"))
        assertNull(recruitmentCodeResource("active"))
    }

    @Test
    fun `requirement copy follows current language and falls back without changing submitted text`() {
        val copy = RecruitmentLocalizedCopy("Profile", "Profil", "الملف")
        assertEquals("الملف", copy.inLanguage("ar-MA"))
        assertEquals("Profil", copy.inLanguage("fr_MA"))
        assertEquals("Profile", copy.inLanguage("de"))
        assertEquals("Profil", copy.copy(ar = "").inLanguage("ar"))
        assertEquals("الملف", copy.copy(en = "", fr = "").inLanguage("en"))
        assertEquals("الملف", copy.ar)
    }

    @Test
    fun `requirement draft validates backend code and localized copy boundaries`() {
        assertNotNull(RequirementItemDraft().toInputOrNull())
        assertNull(RequirementItemDraft(requirementCode = "bad code").toInputOrNull())
        assertNull(
            RequirementItemDraft(
                evidenceType = "CREDENTIAL",
                validityRule = "CREDENTIAL_VERIFIED",
                referenceType = "",
            ).toInputOrNull(),
        )
        assertEquals(
            "DRIVER_LICENSE",
            RequirementItemDraft(
                evidenceType = "CREDENTIAL",
                validityRule = "CREDENTIAL_VERIFIED",
                referenceType = "DRIVER_LICENSE",
            ).toInputOrNull()?.referenceTypeCode,
        )
    }

    @Test
    fun `effective timestamps require an explicit timezone`() {
        assertTrue("2026-08-24T12:00:00Z".hasTimezone())
        assertTrue("2026-08-24T12:00:00+01:00".hasTimezone())
        assertFalse("2026-08-24T12:00:00".hasTimezone())
    }

    @Test
    fun `protected document download requires clean scan supported browser and idle interaction`() {
        assertTrue(canDownloadProtectedDocument(true, "CLEAN", false))
        assertFalse(canDownloadProtectedDocument(false, "CLEAN", false))
        assertFalse(canDownloadProtectedDocument(true, "PENDING", false))
        assertFalse(canDownloadProtectedDocument(true, "CLEAN", true))
    }
}
