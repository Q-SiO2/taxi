package org.example.taximobile.operations.data

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.parameter
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import org.example.taximobile.operations.model.AdministrativeGrantRecord
import org.example.taximobile.operations.model.AdministrativeGrantChangeRequestRecord
import org.example.taximobile.operations.model.AuditLogRecord
import org.example.taximobile.operations.model.CityConfigurationRecord
import org.example.taximobile.operations.model.CityLifecycleTransitionRequest
import org.example.taximobile.operations.model.CityRecord
import org.example.taximobile.operations.model.DriverApplicationDecisionRequest
import org.example.taximobile.operations.model.CityAuthorizationDecisionRequest
import org.example.taximobile.operations.model.DriverOnboardingAggregateRecord
import org.example.taximobile.operations.model.DriverRequirementVersionCommandRequest
import org.example.taximobile.operations.model.DriverRequirementVersionCreateRequest
import org.example.taximobile.operations.model.DriverRequirementVersionRecord
import org.example.taximobile.operations.model.DriverRequirementVersionUpdateRequest
import org.example.taximobile.operations.model.LogoutResponse
import org.example.taximobile.operations.model.MANAGE_DRIVER_REQUIREMENTS
import org.example.taximobile.operations.model.MANAGE_SCHEDULING_POLICY
import org.example.taximobile.operations.model.MANAGE_SCOPED_STAFF_GRANTS
import org.example.taximobile.operations.model.MarketRecord
import org.example.taximobile.operations.model.OperationsLoginRequest
import org.example.taximobile.operations.model.OperationsLoginEnvelope
import org.example.taximobile.operations.model.OperationsLoginResult
import org.example.taximobile.operations.model.OperationsMfaStepUpRequest
import org.example.taximobile.operations.model.OperationsMfaStepUpResponse
import org.example.taximobile.operations.model.OperationsMfaVerificationRequest
import org.example.taximobile.operations.model.OperationsDriverApplicationDetail
import org.example.taximobile.operations.model.OperationsDriverApplicationSummary
import org.example.taximobile.operations.model.AnalyticsMetricDefinitionList
import org.example.taximobile.operations.model.OperationalMetricFactList
import org.example.taximobile.operations.model.OperationsAnalyticsSnapshot
import org.example.taximobile.operations.model.OperationsRefreshRequest
import org.example.taximobile.operations.model.OperationsScope
import org.example.taximobile.operations.model.OperationsSession
import org.example.taximobile.operations.model.OperationsSnapshot
import org.example.taximobile.operations.model.OperationsTokenEnvelope
import org.example.taximobile.operations.model.OperationsTokens
import org.example.taximobile.operations.model.OperatorCityAssignment
import org.example.taximobile.operations.model.OperatorRecord
import org.example.taximobile.operations.model.PagedResponse
import org.example.taximobile.operations.model.REVIEW_DRIVER_APPLICATIONS
import org.example.taximobile.operations.model.ReadinessDecisionRequest
import org.example.taximobile.operations.model.RolloutOverview
import org.example.taximobile.operations.model.ScheduledBookingExceptionRecord
import org.example.taximobile.operations.model.ServiceAreaVersionRecord
import org.example.taximobile.operations.model.VIEW_SCOPED_AUDIT
import org.example.taximobile.operations.model.VIEW_SCOPED_OPERATIONAL_AGGREGATES
import org.example.taximobile.operations.model.toInMemoryTokens
import org.example.taximobile.operations.model.toLoginResult

class OperationsApiException(
    val statusCode: Int,
    override val message: String,
) : RuntimeException(message)

data class ProtectedDriverDocumentDownload(
    val bytes: ByteArray,
    val mediaType: String,
    val fileName: String,
)

interface OperationsGateway {
    val accountSecurity: AccountSecurityGateway
    val staffAccess: StaffAccessGateway
    val controlPlane: ControlPlaneGateway
    val pricingEconomics: PricingEconomicsGateway
    val fixedRoutes: FixedRoutesGateway
    val caseOperations: CaseOperationsGateway
    val paymentOperations: PaymentOperationsGateway
    val securityIncidents: SecurityIncidentGateway

    suspend fun login(identifier: String, password: String): OperationsLoginResult
    suspend fun verifyMfa(challengeId: String, code: String): OperationsTokens
    suspend fun stepUpMfa(accessToken: String, code: String): OperationsMfaStepUpResponse
    suspend fun refresh(refreshToken: String?, csrfToken: String?): OperationsTokens
    suspend fun session(accessToken: String): OperationsSession
    suspend fun logout(accessToken: String)

    suspend fun loadSnapshot(
        accessToken: String,
        session: OperationsSession,
        scope: OperationsScope,
    ): OperationsSnapshot

    suspend fun transitionCity(
        accessToken: String,
        city: CityRecord,
        targetStatus: String,
        reason: String,
    ): CityRecord

    suspend fun decideCityReadiness(
        accessToken: String,
        configuration: CityConfigurationRecord,
        gateCode: String,
        status: String,
        evidenceReference: String,
    ): CityConfigurationRecord

    suspend fun createDriverRequirementVersion(
        accessToken: String,
        cityId: String,
        request: DriverRequirementVersionCreateRequest,
    ): DriverRequirementVersionRecord

    suspend fun updateDriverRequirementVersion(
        accessToken: String,
        versionId: String,
        request: DriverRequirementVersionUpdateRequest,
    ): DriverRequirementVersionRecord

    suspend fun transitionDriverRequirementVersion(
        accessToken: String,
        version: DriverRequirementVersionRecord,
        targetStatus: String,
        reason: String,
    ): DriverRequirementVersionRecord

    suspend fun driverApplication(
        accessToken: String,
        applicationId: String,
    ): OperationsDriverApplicationDetail

    suspend fun downloadDriverApplicationDocument(
        accessToken: String,
        applicationId: String,
        documentId: String,
    ): ProtectedDriverDocumentDownload

    suspend fun decideDriverApplication(
        accessToken: String,
        applicationId: String,
        idempotencyKey: String,
        request: DriverApplicationDecisionRequest,
    ): OperationsDriverApplicationDetail

    suspend fun decideCityAuthorization(
        accessToken: String,
        applicationId: String,
        idempotencyKey: String,
        request: CityAuthorizationDecisionRequest,
    ): OperationsDriverApplicationDetail
}

class KtorOperationsGateway(
    private val client: HttpClient,
    apiBaseUrl: String,
) : OperationsGateway {
    override val accountSecurity: AccountSecurityGateway = KtorAccountSecurityGateway(client, apiBaseUrl)
    override val staffAccess: StaffAccessGateway = KtorStaffAccessGateway(client, apiBaseUrl)
    override val controlPlane: ControlPlaneGateway = KtorControlPlaneGateway(client, apiBaseUrl)
    override val pricingEconomics: PricingEconomicsGateway = KtorPricingEconomicsGateway(client, apiBaseUrl)
    override val fixedRoutes: FixedRoutesGateway = KtorFixedRoutesGateway(client, apiBaseUrl)
    override val caseOperations: CaseOperationsGateway = KtorCaseOperationsGateway(client, apiBaseUrl)
    override val paymentOperations: PaymentOperationsGateway = KtorPaymentOperationsGateway(client, apiBaseUrl)
    override val securityIncidents: SecurityIncidentGateway = KtorSecurityIncidentGateway(client, apiBaseUrl)
    private val endpoints = OperationsApiEndpoints(apiBaseUrl)
    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    override suspend fun login(identifier: String, password: String): OperationsLoginResult {
        val response = client.post(endpoints.url("operations/auth/login")) {
            contentType(ContentType.Application.Json)
            setBody(OperationsLoginRequest(identifier = identifier.trim(), password = password))
        }
        return response.decode<OperationsLoginEnvelope>().toLoginResult()
    }

    override suspend fun verifyMfa(challengeId: String, code: String): OperationsTokens =
        client.post(endpoints.url("operations/auth/mfa/verify")) {
            contentType(ContentType.Application.Json)
            setBody(OperationsMfaVerificationRequest(challengeId, code.trim()))
        }.decode<OperationsTokenEnvelope>().toInMemoryTokens()

    override suspend fun stepUpMfa(
        accessToken: String,
        code: String,
    ): OperationsMfaStepUpResponse = client.post(endpoints.url("operations/auth/mfa/step-up")) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(OperationsMfaStepUpRequest(code.trim()))
    }.decode()

    override suspend fun refresh(refreshToken: String?, csrfToken: String?): OperationsTokens {
        val response = client.post(endpoints.url("operations/auth/refresh")) {
            contentType(ContentType.Application.Json)
            csrfToken?.let { header("X-CSRF-Token", it) }
            refreshToken?.let { setBody(OperationsRefreshRequest(it)) }
        }
        return response.decode<OperationsTokenEnvelope>().toInMemoryTokens()
    }

    override suspend fun session(accessToken: String): OperationsSession =
        client.get(endpoints.url("operations/auth/session")) { authorize(accessToken) }.decode()

    override suspend fun logout(accessToken: String) {
        client.post(endpoints.url("operations/auth/logout")) { authorize(accessToken) }
            .decode<LogoutResponse>()
    }

    override suspend fun loadSnapshot(
        accessToken: String,
        session: OperationsSession,
        scope: OperationsScope,
    ): OperationsSnapshot = coroutineScope {
        // Keep the first browser batch below common HTTP/1.1 per-origin limits.
        // Issuing every preflighted request at once caused an intermittent
        // first-login fetch failure before one request reached the API. Each
        // endpoint still enforces its own grant and SQL scope.
        val markets = async {
            client.get(endpoints.url("operations/markets")) {
                authorize(accessToken)
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<MarketRecord>>()
        }
        val cities = async {
            client.get(endpoints.url("operations/cities")) {
                authorize(accessToken)
                scope.marketId?.let { parameter("market_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<CityRecord>>()
        }
        val operators = async {
            client.get(endpoints.url("operations/operators")) {
                authorize(accessToken)
                scope.marketId?.let { parameter("market_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<OperatorRecord>>()
        }
        val assignments = async {
            client.get(endpoints.url("operations/operator-city-assignments")) {
                authorize(accessToken)
                scope.operatorId?.let { parameter("operator_id", it) }
                scope.cityId?.let { parameter("city_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<OperatorCityAssignment>>()
        }
        val rollout = async {
            client.get(endpoints.url("operations/rollout-overview")) {
                authorize(accessToken)
            }.decode<RolloutOverview>()
        }

        val marketPage = markets.await()
        val cityPage = cities.await()
        val operatorPage = operators.await()
        val assignmentPage = assignments.await()
        val rolloutOverview = rollout.await()
        val detailCityId = scope.cityId ?: cityPage.items.firstOrNull()?.id

        // Permission-sensitive and city-detail reads form a second bounded
        // batch after the five control-plane summary requests complete.
        val grants = if (session.hasPermission(MANAGE_SCOPED_STAFF_GRANTS)) async {
            client.get(endpoints.url("operations/administrative-grants")) {
                authorize(accessToken)
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<AdministrativeGrantRecord>>()
        } else null
        val grantRequests = if (session.hasPermission(MANAGE_SCOPED_STAFF_GRANTS)) async {
            client.get(endpoints.url("operations/administrative-grant-requests")) {
                authorize(accessToken)
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<AdministrativeGrantChangeRequestRecord>>()
        } else null
        val audit = if (session.hasPermission(VIEW_SCOPED_AUDIT)) async {
            client.get(endpoints.url("operations/audit-logs")) {
                authorize(accessToken)
                scope.operatorId?.let { parameter("operator_id", it) }
                scope.cityId?.let { parameter("city_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<AuditLogRecord>>()
        } else null
        val serviceAreas = detailCityId?.let { cityId ->
            async {
                client.get(endpoints.url("operations/cities/$cityId/service-area-versions")) {
                    authorize(accessToken)
                    parameter("page", 1)
                    parameter("limit", 100)
                }.decode<PagedResponse<ServiceAreaVersionRecord>>()
            }
        }
        val configurations = detailCityId?.let { cityId ->
            async {
                client.get(endpoints.url("operations/cities/$cityId/configuration-versions")) {
                    authorize(accessToken)
                    parameter("page", 1)
                    parameter("limit", 100)
                }.decode<PagedResponse<CityConfigurationRecord>>()
            }
        }

        val grantPage = grants?.await()
        val grantRequestPage = grantRequests?.await()
        val auditPage = audit?.await()
        val serviceAreaPage = serviceAreas?.await()
        val configurationPage = configurations?.await()

        // Recruitment and pricing reads form a third bounded batch. Every
        // endpoint independently enforces its named permission and selected
        // city/operator conjunction; browser filtering is never authority.
        val requirementVersions = if (
            detailCityId != null && session.hasPermission(MANAGE_DRIVER_REQUIREMENTS)
        ) async {
            client.get(endpoints.url("operations/cities/$detailCityId/driver-requirement-versions")) {
                authorize(accessToken)
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<DriverRequirementVersionRecord>>()
        } else null
        val driverApplications = if (session.hasPermission(REVIEW_DRIVER_APPLICATIONS)) async {
            client.get(endpoints.url("operations/driver-applications")) {
                authorize(accessToken)
                detailCityId?.let { parameter("city_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<OperationsDriverApplicationSummary>>()
        } else null
        val onboardingAggregate = if (
            detailCityId != null && session.hasPermission(VIEW_SCOPED_OPERATIONAL_AGGREGATES)
        ) async {
            client.get(endpoints.url("operations/cities/$detailCityId/operational-aggregates")) {
                authorize(accessToken)
            }.decode<DriverOnboardingAggregateRecord>()
        } else null
        val pricingSnapshot = if (
            detailCityId != null && session.permissions.any {
                it in org.example.taximobile.operations.model.PRICING_ECONOMICS_PERMISSIONS
            }
        ) async {
            pricingEconomics.loadPricingEconomics(
                accessToken = accessToken,
                session = session,
                cityId = detailCityId,
                operatorId = scope.operatorId,
            )
        } else null
        val routeSnapshot = if (
            detailCityId != null && scope.operatorId != null &&
            session.hasPermission(org.example.taximobile.operations.model.MANAGE_FIXED_ROUTES)
        ) async {
            fixedRoutes.list(accessToken, detailCityId, scope.operatorId)
        } else null
        val routeFareOptions = if (
            detailCityId != null && scope.operatorId != null &&
            session.hasPermission(org.example.taximobile.operations.model.MANAGE_FIXED_ROUTES)
        ) async {
            fixedRoutes.fareOptions(accessToken, detailCityId, scope.operatorId)
        } else null
        val scheduledExceptions = if (
            session.hasPermission(MANAGE_SCHEDULING_POLICY)
        ) async {
            client.get(endpoints.url("operations/scheduled-bookings")) {
                authorize(accessToken)
                detailCityId?.let { parameter("city_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<ScheduledBookingExceptionRecord>>()
        } else null

        val requirementPage = requirementVersions?.await()
        val applicationPage = driverApplications?.await()
        val onboardingSummary = onboardingAggregate?.await()
        val economicsSnapshot = pricingSnapshot?.await()
        val fixedRoutePage = routeSnapshot?.await()
        val fareOptions = routeFareOptions?.await().orEmpty()
        val scheduledExceptionPage = scheduledExceptions?.await()

        // Analytics is intentionally a fourth, sequential browser batch. This
        // avoids reopening the preflight fan-out that previously made first
        // login unreliable, while both API reads still enforce exact city scope.
        val analyticsSnapshot = if (
            detailCityId != null && session.hasPermission(VIEW_SCOPED_OPERATIONAL_AGGREGATES)
        ) {
            val definitions = client.get(endpoints.url("operations/analytics/definitions")) {
                authorize(accessToken)
            }.decode<AnalyticsMetricDefinitionList>()
            val facts = client.get(endpoints.url("operations/analytics/facts")) {
                authorize(accessToken)
                parameter("city_id", detailCityId)
            }.decode<OperationalMetricFactList>()
            OperationsAnalyticsSnapshot(definitions.items, facts)
        } else null

        // Restricted case queues are a final bounded batch. They are loaded
        // only for explicit support/safety permissions and every endpoint
        // independently applies SQL city scope before counts or rows.
        val caseOperationsSnapshot = if (
            session.hasPermission(org.example.taximobile.operations.model.MANAGE_SUPPORT_CASES) ||
            session.hasPermission(org.example.taximobile.operations.model.MANAGE_SAFETY_CASES)
        ) {
            caseOperations.load(accessToken, session, detailCityId)
        } else null

        val paymentOperationsSnapshot = if (
            session.hasPermission(org.example.taximobile.operations.model.MANAGE_PAYMENT_CAPABILITIES) ||
            session.hasPermission(org.example.taximobile.operations.model.RECONCILE_PAYMENTS)
        ) {
            paymentOperations.load(accessToken, session, detailCityId, scope.operatorId)
        } else null

        val securityIncidentSnapshot = if (
            session.hasPermission(org.example.taximobile.operations.model.MANAGE_SECURITY_INCIDENTS)
        ) {
            securityIncidents.load(accessToken, scope.marketId)
        } else null

        OperationsSnapshot(
            markets = marketPage,
            cities = cityPage,
            operators = operatorPage,
            assignments = assignmentPage,
            rollout = rolloutOverview,
            grants = grantPage,
            grantRequests = grantRequestPage,
            auditLogs = auditPage,
            serviceAreas = serviceAreaPage,
            configurations = configurationPage,
            driverRequirementVersions = requirementPage,
            driverApplications = applicationPage,
            onboardingAggregate = onboardingSummary,
            pricingEconomics = economicsSnapshot,
            fixedRoutes = fixedRoutePage,
            fixedRouteFareOptions = fareOptions,
            scheduledBookingExceptions = scheduledExceptionPage,
            analytics = analyticsSnapshot,
            caseOperations = caseOperationsSnapshot,
            paymentOperations = paymentOperationsSnapshot,
            securityIncidents = securityIncidentSnapshot,
        )
    }

    override suspend fun transitionCity(
        accessToken: String,
        city: CityRecord,
        targetStatus: String,
        reason: String,
    ): CityRecord {
        val response = client.post(endpoints.url("operations/cities/${city.id}/lifecycle-transitions")) {
            authorize(accessToken)
            contentType(ContentType.Application.Json)
            setBody(
                CityLifecycleTransitionRequest(
                    targetStatus = targetStatus,
                    expectedVersion = city.optimisticVersion,
                    reason = reason.trim(),
                )
            )
        }
        return response.decode()
    }

    override suspend fun decideCityReadiness(
        accessToken: String,
        configuration: CityConfigurationRecord,
        gateCode: String,
        status: String,
        evidenceReference: String,
    ): CityConfigurationRecord = client.post(
        endpoints.url("operations/city-configuration-versions/${configuration.id}/readiness-decisions"),
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(
            ReadinessDecisionRequest(
                gateCode = gateCode,
                status = status,
                nonSecretEvidenceReference = evidenceReference.trim(),
                expectedConfigurationVersion = configuration.optimisticVersion,
            )
        )
    }.decode()

    override suspend fun createDriverRequirementVersion(
        accessToken: String,
        cityId: String,
        request: DriverRequirementVersionCreateRequest,
    ): DriverRequirementVersionRecord = client.post(
        endpoints.url("operations/cities/$cityId/driver-requirement-versions"),
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun updateDriverRequirementVersion(
        accessToken: String,
        versionId: String,
        request: DriverRequirementVersionUpdateRequest,
    ): DriverRequirementVersionRecord = client.patch(
        endpoints.url("operations/driver-requirement-versions/$versionId"),
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun transitionDriverRequirementVersion(
        accessToken: String,
        version: DriverRequirementVersionRecord,
        targetStatus: String,
        reason: String,
    ): DriverRequirementVersionRecord {
        val action = when (targetStatus) {
            "IN_REVIEW" -> "submit"
            "ACTIVE" -> "activate"
            else -> throw IllegalArgumentException("Unsupported requirement target $targetStatus")
        }
        return client.post(endpoints.url("operations/driver-requirement-versions/${version.id}/$action")) {
            authorize(accessToken)
            contentType(ContentType.Application.Json)
            setBody(DriverRequirementVersionCommandRequest(version.optimisticVersion, reason.trim()))
        }.decode()
    }

    override suspend fun driverApplication(
        accessToken: String,
        applicationId: String,
    ): OperationsDriverApplicationDetail = client.get(
        endpoints.url("operations/driver-applications/$applicationId"),
    ) { authorize(accessToken) }.decode()

    override suspend fun downloadDriverApplicationDocument(
        accessToken: String,
        applicationId: String,
        documentId: String,
    ): ProtectedDriverDocumentDownload {
        val response = client.get(
            endpoints.url("operations/driver-applications/$applicationId/documents/$documentId"),
        ) { authorize(accessToken) }
        if (!response.status.isSuccess()) {
            val body = response.bodyAsText()
            throw OperationsApiException(response.status.value, errorDetail(body, response.status.value))
        }
        val mediaType = response.headers[HttpHeaders.ContentType]
            ?.substringBefore(';')
            ?.trim()
            ?.lowercase()
            ?.takeIf { it in PROTECTED_DOCUMENT_MEDIA_TYPES }
            ?: throw OperationsApiException(502, "The protected document response type was invalid.")
        val bytes = response.body<ByteArray>()
        if (bytes.isEmpty() || bytes.size > MAX_PROTECTED_DOCUMENT_BYTES) {
            throw OperationsApiException(502, "The protected document response size was invalid.")
        }
        val extension = when (mediaType) {
            "application/pdf" -> "pdf"
            "image/jpeg" -> "jpg"
            else -> "png"
        }
        return ProtectedDriverDocumentDownload(
            bytes = bytes,
            mediaType = mediaType,
            fileName = "driver-document-${documentId.take(12)}.$extension",
        )
    }

    override suspend fun decideDriverApplication(
        accessToken: String,
        applicationId: String,
        idempotencyKey: String,
        request: DriverApplicationDecisionRequest,
    ): OperationsDriverApplicationDetail = client.post(
        endpoints.url("operations/driver-applications/$applicationId/decisions"),
    ) {
        authorize(accessToken)
        header("Idempotency-Key", idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun decideCityAuthorization(
        accessToken: String,
        applicationId: String,
        idempotencyKey: String,
        request: CityAuthorizationDecisionRequest,
    ): OperationsDriverApplicationDetail = client.post(
        endpoints.url("operations/driver-applications/$applicationId/authorization/decisions"),
    ) {
        authorize(accessToken)
        header("Idempotency-Key", idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    private fun io.ktor.client.request.HttpRequestBuilder.authorize(accessToken: String) {
        header(HttpHeaders.Authorization, "Bearer $accessToken")
    }

    private suspend inline fun <reified T> HttpResponse.decode(): T {
        val body = bodyAsText()
        if (!status.isSuccess()) {
            throw OperationsApiException(status.value, errorDetail(body, status.value))
        }
        return try {
            json.decodeFromString<T>(body)
        } catch (error: Throwable) {
            throw OperationsApiException(
                status.value,
                "The operations API returned an unreadable response.",
            )
        }
    }

    private fun errorDetail(body: String, statusCode: Int): String {
        if (body.isBlank()) return "The operations API returned HTTP $statusCode."
        return runCatching {
            val detail = json.parseToJsonElement(body).jsonObject["detail"]
            detail.toDisplayMessage() ?: "The operations API returned HTTP $statusCode."
        }.getOrElse { "The operations API returned HTTP $statusCode." }
    }
}

private const val MAX_PROTECTED_DOCUMENT_BYTES = 10 * 1024 * 1024
private val PROTECTED_DOCUMENT_MEDIA_TYPES = setOf("application/pdf", "image/jpeg", "image/png")

private fun JsonElement?.toDisplayMessage(): String? = when (this) {
    is JsonPrimitive -> contentOrNull
    is JsonArray -> mapNotNull { item ->
        when (item) {
            is JsonObject -> (item["msg"] as? JsonPrimitive)?.contentOrNull
            is JsonPrimitive -> item.contentOrNull
            else -> null
        }
    }.joinToString(" ").ifBlank { null }
    else -> null
}
