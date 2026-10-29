package org.example.taximobile.operations.data

import io.ktor.client.HttpClient
import io.ktor.client.request.header
import io.ktor.client.request.get
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
import kotlinx.serialization.json.Json
import kotlinx.serialization.encodeToString
import org.example.taximobile.operations.model.OperatorMembershipRecord
import org.example.taximobile.operations.model.OperatorMembershipPage
import org.example.taximobile.operations.model.OperatorMembershipCreateRequest
import org.example.taximobile.operations.model.OperatorMembershipUpdateRequest
import org.example.taximobile.operations.model.OperatorMembershipPolicyRequest
import org.example.taximobile.operations.model.operatorMembershipWireJson
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import org.example.taximobile.operations.model.CityConfigurationCreateRequest
import org.example.taximobile.operations.model.CityConfigurationRecord
import org.example.taximobile.operations.model.CityCreateRequest
import org.example.taximobile.operations.model.CityRecord
import org.example.taximobile.operations.model.ConfigurationCommandRequest
import org.example.taximobile.operations.model.OperatorCityAssignment
import org.example.taximobile.operations.model.OperatorCityAssignmentCreateRequest
import org.example.taximobile.operations.model.OperatorCityAssignmentRetireRequest
import org.example.taximobile.operations.model.OperatorCreateRequest
import org.example.taximobile.operations.model.OperatorRecord
import org.example.taximobile.operations.model.OperatorStatusUpdateRequest
import org.example.taximobile.operations.model.ServiceAreaTransitionRequest
import org.example.taximobile.operations.model.ServiceAreaVersionCreateRequest
import org.example.taximobile.operations.model.ServiceAreaVersionRecord

interface ControlPlaneGateway {
    suspend fun memberships(accessToken: String, operatorId: String, page: Int): OperatorMembershipPage
    suspend fun enrollMember(accessToken: String, operatorId: String, key: String, request: OperatorMembershipCreateRequest): OperatorMembershipRecord
    suspend fun updateMember(accessToken: String, operatorId: String, memberId: String, key: String, request: OperatorMembershipUpdateRequest): OperatorMembershipRecord
    suspend fun updateMembershipPolicy(accessToken: String, operatorId: String, request: OperatorMembershipPolicyRequest): OperatorRecord
    suspend fun createCity(accessToken: String, request: CityCreateRequest): CityRecord
    suspend fun createOperator(accessToken: String, request: OperatorCreateRequest): OperatorRecord
    suspend fun updateOperatorStatus(
        accessToken: String,
        operatorId: String,
        request: OperatorStatusUpdateRequest,
    ): OperatorRecord

    suspend fun createAssignment(
        accessToken: String,
        request: OperatorCityAssignmentCreateRequest,
    ): OperatorCityAssignment

    suspend fun retireAssignment(
        accessToken: String,
        assignmentId: String,
        request: OperatorCityAssignmentRetireRequest,
    ): OperatorCityAssignment

    suspend fun createServiceArea(
        accessToken: String,
        cityId: String,
        request: ServiceAreaVersionCreateRequest,
    ): ServiceAreaVersionRecord

    suspend fun transitionServiceArea(
        accessToken: String,
        area: ServiceAreaVersionRecord,
        targetStatus: String,
        reason: String,
    ): ServiceAreaVersionRecord

    suspend fun createConfiguration(
        accessToken: String,
        cityId: String,
        request: CityConfigurationCreateRequest,
    ): CityConfigurationRecord

    suspend fun transitionConfiguration(
        accessToken: String,
        configuration: CityConfigurationRecord,
        targetStatus: String,
        reason: String,
    ): CityConfigurationRecord
}

class KtorControlPlaneGateway(
    private val client: HttpClient,
    apiBaseUrl: String,
) : ControlPlaneGateway {
    private val endpoints = OperationsApiEndpoints(apiBaseUrl)
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }
    // Complete record edits must carry nulls so staff can explicitly clear dates
    // or numbers. The application-wide nullable-field omission is unsuitable.

    override suspend fun memberships(accessToken: String, operatorId: String, page: Int): OperatorMembershipPage =
        client.get(endpoints.url("operations/operators/$operatorId/memberships")) {
            authorize(accessToken)
            parameter("page", page)
            parameter("limit", 20)
        }.decode()

    override suspend fun enrollMember(accessToken: String, operatorId: String, key: String, request: OperatorMembershipCreateRequest): OperatorMembershipRecord =
        client.post(endpoints.url("operations/operators/$operatorId/memberships")) {
            authorize(accessToken)
            header("Idempotency-Key", key)
            contentType(ContentType.Application.Json)
            setBody(operatorMembershipWireJson.encodeToString(request))
        }.decode()

    override suspend fun updateMember(accessToken: String, operatorId: String, memberId: String, key: String, request: OperatorMembershipUpdateRequest): OperatorMembershipRecord =
        client.patch(endpoints.url("operations/operators/$operatorId/memberships/$memberId")) {
            authorize(accessToken)
            header("Idempotency-Key", key)
            contentType(ContentType.Application.Json)
            setBody(operatorMembershipWireJson.encodeToString(request))
        }.decode()

    override suspend fun updateMembershipPolicy(accessToken: String, operatorId: String, request: OperatorMembershipPolicyRequest): OperatorRecord =
        client.patch(endpoints.url("operations/operators/$operatorId")) {
            authorize(accessToken)
            contentType(ContentType.Application.Json)
            setBody(request)
        }.decode()

    override suspend fun createCity(accessToken: String, request: CityCreateRequest): CityRecord =
        client.post(endpoints.url("operations/cities")) {
            authorize(accessToken)
            contentType(ContentType.Application.Json)
            setBody(request)
        }.decode()

    override suspend fun createOperator(accessToken: String, request: OperatorCreateRequest): OperatorRecord =
        client.post(endpoints.url("operations/operators")) {
            authorize(accessToken)
            contentType(ContentType.Application.Json)
            setBody(request)
        }.decode()

    override suspend fun updateOperatorStatus(
        accessToken: String,
        operatorId: String,
        request: OperatorStatusUpdateRequest,
    ): OperatorRecord = client.patch(endpoints.url("operations/operators/$operatorId")) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun createAssignment(
        accessToken: String,
        request: OperatorCityAssignmentCreateRequest,
    ): OperatorCityAssignment = client.post(endpoints.url("operations/operator-city-assignments")) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun retireAssignment(
        accessToken: String,
        assignmentId: String,
        request: OperatorCityAssignmentRetireRequest,
    ): OperatorCityAssignment = client.post(
        endpoints.url("operations/operator-city-assignments/$assignmentId/retire")
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun createServiceArea(
        accessToken: String,
        cityId: String,
        request: ServiceAreaVersionCreateRequest,
    ): ServiceAreaVersionRecord = client.post(
        endpoints.url("operations/cities/$cityId/service-area-versions")
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun transitionServiceArea(
        accessToken: String,
        area: ServiceAreaVersionRecord,
        targetStatus: String,
        reason: String,
    ): ServiceAreaVersionRecord = client.post(
        endpoints.url("operations/service-area-versions/${area.id}/transitions")
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(ServiceAreaTransitionRequest(targetStatus, area.optimisticVersion, reason.trim()))
    }.decode()

    override suspend fun createConfiguration(
        accessToken: String,
        cityId: String,
        request: CityConfigurationCreateRequest,
    ): CityConfigurationRecord = client.post(
        endpoints.url("operations/cities/$cityId/configuration-versions")
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun transitionConfiguration(
        accessToken: String,
        configuration: CityConfigurationRecord,
        targetStatus: String,
        reason: String,
    ): CityConfigurationRecord = client.post(
        endpoints.url("operations/city-configuration-versions/${configuration.id}/${commandPath(targetStatus)}")
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(ConfigurationCommandRequest(configuration.optimisticVersion, reason.trim()))
    }.decode()

    private fun commandPath(targetStatus: String): String = when (targetStatus) {
        "IN_REVIEW" -> "submit"
        "APPROVED" -> "approve"
        "ACTIVE" -> "activate"
        else -> error("Unsupported configuration target $targetStatus")
    }

    private fun io.ktor.client.request.HttpRequestBuilder.authorize(accessToken: String) {
        header(HttpHeaders.Authorization, "Bearer $accessToken")
    }

    private suspend inline fun <reified T> HttpResponse.decode(): T {
        val body = bodyAsText()
        if (!status.isSuccess()) {
            throw OperationsApiException(status.value, detail(body).ifBlank { "Request failed (${status.value})." })
        }
        return json.decodeFromString(body)
    }

    private fun detail(body: String): String = runCatching {
        when (val element = json.parseToJsonElement(body)) {
            is JsonObject -> detailValue(element["detail"])
            else -> body
        }
    }.getOrDefault(body)

    private fun detailValue(value: JsonElement?): String = when (value) {
        is JsonPrimitive -> value.contentOrNull.orEmpty()
        is JsonArray -> value.joinToString("; ") { item ->
            (item as? JsonObject)?.get("msg")?.let(::detailValue).orEmpty()
        }
        is JsonObject -> value["msg"]?.let(::detailValue).orEmpty().ifBlank { value.toString() }
        null -> ""
    }
}
