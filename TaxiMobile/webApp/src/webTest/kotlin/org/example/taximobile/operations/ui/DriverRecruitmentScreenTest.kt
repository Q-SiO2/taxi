package org.example.taximobile.operations.ui

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class DriverRecruitmentScreenTest {
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
