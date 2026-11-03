package org.example.taximobile.applicant.state

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import org.example.taximobile.data.auth.AuthenticationGateway
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.feature.ui.text.UiMessage
import taximobile.shared.generated.resources.*
import org.example.taximobile.domain.auth.AccountRole
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens
import org.example.taximobile.domain.drivers.*
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator

/** Immediate fake gateways exercise the real coordinator without timers or a network. */
class ApplicantPortalCoordinatorTest {
    @Test
    fun `saved draft notice uses the confirmed revision and resource message without replay`() = withPortal { portal, server, _ ->
        server.records[0] = server.records[0].copy(status = "NOT_STARTED", editable = true)
        portal.refresh()
        val before = requireNotNull(portal.state.value.selectedApplication)
        portal.saveApplication(before.id, before.optimisticVersion, emptyList(), emptyList(), emptyList(), emptyList())
        assertEquals(1, server.updateCalls)
        assertEquals(before.optimisticVersion, server.lastExpectedVersion)
        assertEquals(before.optimisticVersion + 1, portal.state.value.selectedApplication?.optimisticVersion)
        assertEquals(UiMessage(Res.string.web_app_saved_title), portal.state.value.notice?.localizedTitle)
        assertEquals(UiMessage(Res.string.web_app_version_confirmed, listOf(before.optimisticVersion + 1)),
            portal.state.value.notice?.localizedDetail)
        assertEquals(null, portal.state.value.busyLabel)
    }

    @Test
    fun `save followed by failed detail read reports uncertainty instead of a success notice`() = withPortal { portal, server, _ ->
        server.records[0] = server.records[0].copy(status = "NOT_STARTED", editable = true)
        portal.refresh()
        val before = requireNotNull(portal.state.value.selectedApplication)
        server.failDetail = true
        portal.saveApplication(before.id, before.optimisticVersion, emptyList(), emptyList(), emptyList(), emptyList())
        assertEquals(1, server.updateCalls)
        assertEquals(null, portal.state.value.notice)
        assertEquals(UiMessage(Res.string.web_connection_unavailable), portal.state.value.error?.localizedDetail)
        assertEquals(null, portal.state.value.busyLabel)
        assertEquals(ApplicantSessionPhase.SIGNED_IN, portal.state.value.sessionPhase)
    }

    @Test
    fun `public catalog service outage stays signed out and can recover without an upload`() {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Unconfined)
        val server = RecruitmentServer().apply { catalogError = ApiRequestException(503, "Unavailable") }
        val portal = ApplicantPortalCoordinator(
            AuthenticationSessionCoordinator(PortalAuth(), InMemoryApplicantTokenStore()),
            server, PortalDriver(), scope, "http://127.0.0.1:8000/api/v1",
        )
        try {
            assertEquals(ApplicantSessionPhase.SIGNED_OUT, portal.state.value.sessionPhase)
            assertEquals(UiMessage(Res.string.web_catalog_unavailable), portal.state.value.error?.localizedDetail)
            assertEquals(null, portal.state.value.account)
            assertEquals(true, portal.state.value.catalogUnavailable)
            server.catalogError = null
            portal.refresh()
            assertEquals(null, portal.state.value.error)
            assertEquals(false, portal.state.value.catalogUnavailable)
            assertEquals(ApplicantSessionPhase.SIGNED_OUT, portal.state.value.sessionPhase)
        } finally {
            scope.cancel()
        }
    }

    @Test
    fun `refresh updates open detail after an independent reviewer decision`() = withPortal { portal, server, _ ->
        assertEquals("SUBMITTED", portal.state.value.selectedApplication?.status)
        server.records[0] = server.records[0].copy(
            status = "UNDER_REVIEW", optimisticVersion = 3,
        )
        portal.refresh()
        assertEquals("UNDER_REVIEW", portal.state.value.applications.first().status)
        assertEquals("UNDER_REVIEW", portal.state.value.selectedApplication?.status)
        assertEquals(3, portal.state.value.selectedApplication?.optimisticVersion)
        assertEquals(null, portal.state.value.busyLabel)
    }

    @Test
    fun `refresh retains the chosen application instead of choosing the first city`() = withPortal { portal, server, _ ->
        server.records += demoApplication("second", cityId = "second-city")
        portal.selectApplication("second")
        server.records[1] = server.records[1].copy(status = "REJECTED", optimisticVersion = 4)
        portal.refresh()
        assertEquals("second", portal.state.value.selectedApplication?.id)
        assertEquals("REJECTED", portal.state.value.selectedApplication?.status)
        assertEquals(4, portal.state.value.selectedApplication?.optimisticVersion)
    }

    @Test
    fun `vehicle registration reloads requirement completion instead of cached detail`() = withPortal { portal, server, driver ->
        driver.onRegister = {
            server.records[0] = server.records[0].copy(
                complete = false, missingRequiredItemIds = setOf("vehicle"), optimisticVersion = 5,
            )
        }
        portal.registerVehicle(VehicleRegistration("Demo", "Taxi", 2024, "White", "SYNTHETIC-ONLY"))
        assertEquals(false, portal.state.value.selectedApplication?.complete)
        assertEquals(setOf("vehicle"), portal.state.value.selectedApplication?.missingRequiredItemIds)
        assertEquals(5, portal.state.value.selectedApplication?.optimisticVersion)
    }

    @Test
    fun `failed detail refresh reports failure rather than claiming a successful refresh`() = withPortal { portal, server, _ ->
        server.failDetail = true
        portal.refresh()
        assertNotNull(portal.state.value.error)
        assertEquals(null, portal.state.value.notice)
        assertEquals(null, portal.state.value.busyLabel)
        assertEquals(ApplicantSessionPhase.SIGNED_IN, portal.state.value.sessionPhase)
    }

    private fun withPortal(test: (ApplicantPortalCoordinator, RecruitmentServer, PortalDriver) -> Unit) {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Unconfined)
        val server = RecruitmentServer()
        val driver = PortalDriver()
        val portal = ApplicantPortalCoordinator(
            AuthenticationSessionCoordinator(PortalAuth(), InMemoryApplicantTokenStore()),
            server, driver, scope, "http://127.0.0.1:8000/api/v1",
        )
        try {
            portal.login("synthetic@example.test", "synthetic-test-only")
            assertEquals(ApplicantSessionPhase.SIGNED_IN, portal.state.value.sessionPhase)
            test(portal, server, driver)
        } finally {
            scope.cancel()
        }
    }
}

private fun demoApplication(id: String, cityId: String = "city") = DriverCityApplication(
    id = id, driverId = "driver", cityId = cityId, cityCode = "SYNTHETIC",
    cityName = RecruitmentCopy("Synthetic", "Synthetic", "Synthetic"),
    requirementVersionId = "requirements", requirementVersion = "demo-v1",
    status = "SUBMITTED", optimisticVersion = 2, submissionRevision = 1,
    editable = false, complete = true, missingRequiredItemIds = emptySet(),
    documentUploadAvailable = false, submittedAt = "2026-10-02T00:00:00Z",
    reviewedAt = null, withdrawnAt = null, updatedAt = "2026-10-02T00:00:00Z",
    requirements = emptyList(), answers = emptyList(), evidence = emptyList(),
    documents = emptyList(), latestDecision = null, authorization = null,
)

private class RecruitmentServer : DriverRecruitmentGateway {
    val records = mutableListOf(demoApplication("first"))
    var failDetail = false
    var catalogError: Throwable? = null
    var updateCalls = 0
    var lastExpectedVersion: Int? = null
    override suspend fun recruitingCities(): List<RecruitingCity> {
        catalogError?.let { throw it }
        return emptyList()
    }
    override suspend fun applications() = records.map {
        DriverCityApplicationSummary(
            it.id, it.cityId, it.cityCode, it.cityName, it.requirementVersionId,
            it.requirementVersion, it.status, it.optimisticVersion,
            it.submittedAt, it.reviewedAt, it.updatedAt, null,
        )
    }
    override suspend fun application(applicationId: String): DriverCityApplication {
        if (failDetail) throw AuthenticationNetworkException()
        return records.first { it.id == applicationId }
    }
    override suspend fun createApplication(cityId: String, displayName: String?) = error("Unused")
    override suspend fun updateApplication(
        applicationId: String, expectedVersion: Int,
        answers: List<DriverApplicationAnswerDraft>, evidence: List<DriverApplicationEvidenceDraft>,
        removeAnswerItemIds: List<String>, removeEvidenceItemIds: List<String>,
    ): DriverCityApplication {
        updateCalls++
        lastExpectedVersion = expectedVersion
        val index = records.indexOfFirst { it.id == applicationId }
        val current = records[index]
        check(current.editable)
        check(current.optimisticVersion == expectedVersion)
        return current.copy(optimisticVersion = current.optimisticVersion + 1).also { records[index] = it }
    }
    override suspend fun submitApplication(applicationId: String) = error("Unused")
    override suspend fun withdrawApplication(applicationId: String) = error("Unused")
    override suspend fun uploadDocument(
        applicationId: String, requirementItemId: String, expectedVersion: Int, document: DriverDocumentUpload,
    ) = error("Unused")
    override suspend fun deleteDocument(applicationId: String, documentId: String, expectedVersion: Int) = error("Unused")
}

private class PortalAuth : AuthenticationGateway {
    override suspend fun register(displayName: String, email: String?, phoneNumber: String?, password: String) = error("Unused")
    override suspend fun login(identifier: String, password: String, deviceLabel: String?) = SessionTokens("synthetic-access", "synthetic-refresh")
    override suspend fun refresh(refreshToken: String) = error("Unused")
    override suspend fun logout(accessToken: String) = Unit
    override suspend fun currentAccount(accessToken: String) = CurrentAccount("account", setOf(AccountRole.PASSENGER), "Synthetic")
}

private class PortalDriver : DriverGateway {
    var onRegister: () -> Unit = {}
    override suspend fun vehicles(): List<DriverVehicle> = emptyList()
    override suspend fun credentials(): List<DriverCredential> = emptyList()
    override suspend fun registerVehicle(vehicle: VehicleRegistration): DriverVehicle {
        onRegister()
        return DriverVehicle("vehicle", vehicle.make, vehicle.model, vehicle.color, "ACTIVE", "PENDING")
    }
    override suspend fun apply(displayName: String) = error("Unused")
    override suspend fun profile() = error("Unused")
    override suspend fun verificationStatus() = error("Unused")
    override suspend fun submitVerification() = error("Unused")
    override suspend fun currentAvailability() = error("Unused")
    override suspend fun goOnline(cityId: String?, serviceType: String) = error("Unused")
    override suspend fun goOffline() = error("Unused")
    override suspend fun selectActiveVehicle(vehicleId: String) = error("Unused")
    override suspend fun deactivateVehicle(vehicleId: String) = error("Unused")
    override suspend fun updateLocation(location: Coordinates, observedAt: String, accuracyMeters: Double) =
        error("The applicant portal must not submit driver location")
}
