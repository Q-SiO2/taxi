package org.example.taximobile.data.drivers

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.HttpRequestBuilder
import io.ktor.client.request.get
import io.ktor.client.request.delete
import io.ktor.client.request.forms.MultiPartFormDataContent
import io.ktor.client.request.forms.formData
import io.ktor.client.request.header
import io.ktor.client.request.patch
import io.ktor.client.request.parameter
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.http.ContentType
import io.ktor.http.Headers
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.drivers.ApplicantDecision
import org.example.taximobile.domain.drivers.DriverApplicationAnswer
import org.example.taximobile.domain.drivers.DriverApplicationAnswerDraft
import org.example.taximobile.domain.drivers.DriverApplicationDocument
import org.example.taximobile.domain.drivers.DriverDocumentUpload
import org.example.taximobile.domain.drivers.DriverApplicationEvidence
import org.example.taximobile.domain.drivers.DriverApplicationEvidenceDraft
import org.example.taximobile.domain.drivers.DriverCityApplication
import org.example.taximobile.domain.drivers.DriverCityApplicationSummary
import org.example.taximobile.domain.drivers.DriverCityAuthorization
import org.example.taximobile.domain.drivers.DriverRecruitmentGateway
import org.example.taximobile.domain.drivers.DriverRequirement
import org.example.taximobile.domain.drivers.DriverRequirementEvidenceType
import org.example.taximobile.domain.drivers.RecruitingCity
import org.example.taximobile.domain.drivers.RecruitmentCopy

/** One API boundary shared by native driver onboarding surfaces. */
class KtorDriverRecruitmentGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : DriverRecruitmentGateway {
    override suspend fun recruitingCities(): List<RecruitingCity> = request {
        val response = client.get(api.endpoint("drivers/recruiting-cities"))
        response.requireSuccess("The recruiting-city catalog is unavailable.")
        response.body<RecruitingCityListDto>().items.map(RecruitingCityDto::toDomain)
    }

    override suspend fun applications(): List<DriverCityApplicationSummary> = request {
        val response = client.get(api.endpoint("drivers/me/city-applications")) { authorize() }
        response.requireSuccess("Your city applications could not be loaded.")
        response.body<CityApplicationListDto>().items.map(CityApplicationSummaryDto::toDomain)
    }

    override suspend fun application(applicationId: String): DriverCityApplication = request {
        val response = client.get(api.endpoint("drivers/me/city-applications/$applicationId")) { authorize() }
        response.requireSuccess("This city application could not be loaded.")
        response.body<CityApplicationDto>().toDomain()
    }

    override suspend fun createApplication(cityId: String, displayName: String?): DriverCityApplication = request {
        val response = client.post(api.endpoint("drivers/me/city-applications")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(CreateCityApplicationDto(cityId, displayName?.trim()?.takeIf(String::isNotEmpty)))
        }
        response.requireSuccess("The city application could not be created.")
        response.body<CityApplicationDto>().toDomain()
    }

    override suspend fun updateApplication(
        applicationId: String,
        expectedVersion: Int,
        answers: List<DriverApplicationAnswerDraft>,
        evidence: List<DriverApplicationEvidenceDraft>,
        removeAnswerItemIds: List<String>,
        removeEvidenceItemIds: List<String>,
    ): DriverCityApplication = request {
        val response = client.patch(api.endpoint("drivers/me/city-applications/$applicationId")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(
                UpdateCityApplicationDto(
                    expectedVersion = expectedVersion,
                    answers = answers.takeIf(List<*>::isNotEmpty)?.map(ApplicationAnswerDraftDto::from),
                    evidence = evidence.takeIf(List<*>::isNotEmpty)?.map(ApplicationEvidenceDraftDto::from),
                    removeAnswerItemIds = removeAnswerItemIds,
                    removeEvidenceItemIds = removeEvidenceItemIds,
                ),
            )
        }
        response.requireSuccess("The application changed or could not be saved. Refresh and try again.")
        response.body<CityApplicationDto>().toDomain()
    }

    override suspend fun submitApplication(applicationId: String): DriverCityApplication = request {
        val response = client.post(api.endpoint("drivers/me/city-applications/$applicationId/submit")) {
            authorize()
        }
        response.requireSuccess("The application is incomplete or could not be submitted.")
        response.body<CityApplicationDto>().toDomain()
    }

    override suspend fun withdrawApplication(applicationId: String): DriverCityApplication = request {
        val response = client.post(api.endpoint("drivers/me/city-applications/$applicationId/withdraw")) {
            authorize()
        }
        response.requireSuccess("The application can no longer be withdrawn.")
        response.body<CityApplicationDto>().toDomain()
    }

    override suspend fun uploadDocument(
        applicationId: String,
        requirementItemId: String,
        expectedVersion: Int,
        document: DriverDocumentUpload,
    ): DriverCityApplication = request {
        val safeName = document.fileName
            .filter { it.isLetterOrDigit() || it in setOf('.', '-', '_') }
            .take(120)
            .ifBlank { "driver-document" }
        val response = client.post(
            api.endpoint("drivers/me/city-applications/$applicationId/documents"),
        ) {
            authorize()
            setBody(
                MultiPartFormDataContent(
                    formData {
                        append("requirement_item_id", requirementItemId)
                        append("expected_application_version", expectedVersion.toString())
                        append(
                            "file",
                            document.bytes,
                            Headers.build {
                                append(HttpHeaders.ContentType, document.mediaType)
                                append(
                                    HttpHeaders.ContentDisposition,
                                    "filename=\"$safeName\"",
                                )
                            },
                        )
                    },
                ),
            )
        }
        response.requireSuccess("The protected document could not be uploaded.")
        response.body<CityApplicationDto>().toDomain()
    }

    override suspend fun deleteDocument(
        applicationId: String,
        documentId: String,
        expectedVersion: Int,
    ): DriverCityApplication = request {
        val response = client.delete(
            api.endpoint("drivers/me/city-applications/$applicationId/documents/$documentId"),
        ) {
            authorize()
            parameter("expected_application_version", expectedVersion)
        }
        response.requireSuccess("The protected document could not be deleted.")
        response.body<CityApplicationDto>().toDomain()
    }

    private suspend fun HttpRequestBuilder.authorize() {
        header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
    }

    private fun HttpResponse.requireSuccess(fallback: String) {
        if (status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!status.isSuccess()) throw ApiRequestException(status.value, fallback)
    }

    private suspend fun <T> request(block: suspend () -> T): T = try {
        block()
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (_: Exception) {
        throw AuthenticationNetworkException()
    }
}

@Serializable
private data class LocalizedCopyDto(val en: String, val fr: String, val ar: String) {
    fun toDomain() = RecruitmentCopy(en, fr, ar)
}

@Serializable
private data class RecruitingCityListDto(val items: List<RecruitingCityDto>)

@Serializable
private data class RecruitingCityDto(
    val id: String,
    val code: String,
    @SerialName("localized_name") val localizedName: Map<String, String>,
    val timezone: String,
    @SerialName("lifecycle_status") val lifecycleStatus: String,
    @SerialName("requirement_version_id") val requirementVersionId: String,
    @SerialName("requirement_version") val requirementVersion: String,
) {
    fun toDomain() = RecruitingCity(
        id = id,
        code = code,
        name = localizedName.toCopy(),
        timezone = timezone,
        lifecycleStatus = lifecycleStatus,
        requirementVersionId = requirementVersionId,
        requirementVersion = requirementVersion,
    )
}

@Serializable
private data class RequirementDto(
    val id: String,
    @SerialName("requirement_code") val requirementCode: String,
    @SerialName("evidence_type") val evidenceType: String,
    val required: Boolean,
    @SerialName("validity_rule_code") val validityRuleCode: String,
    @SerialName("reference_type_code") val referenceTypeCode: String? = null,
    @SerialName("display_order") val displayOrder: Int,
    @SerialName("localized_label") val localizedLabel: LocalizedCopyDto,
    @SerialName("localized_description") val localizedDescription: LocalizedCopyDto,
) {
    fun toDomain() = DriverRequirement(
        id = id,
        code = requirementCode,
        evidenceType = DriverRequirementEvidenceType.valueOf(evidenceType),
        required = required,
        validityRule = validityRuleCode,
        referenceType = referenceTypeCode,
        displayOrder = displayOrder,
        label = localizedLabel.toDomain(),
        description = localizedDescription.toDomain(),
    )
}

@Serializable
private data class CityApplicationListDto(val items: List<CityApplicationSummaryDto>)

@Serializable
private data class CityApplicationSummaryDto(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("city_code") val cityCode: String,
    @SerialName("city_name") val cityName: Map<String, String>,
    @SerialName("requirement_version_id") val requirementVersionId: String,
    @SerialName("requirement_version") val requirementVersion: String,
    val status: String,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("reviewed_at") val reviewedAt: String? = null,
    @SerialName("updated_at") val updatedAt: String,
    @SerialName("latest_applicant_message") val latestApplicantMessage: String? = null,
) {
    fun toDomain() = DriverCityApplicationSummary(
        id, cityId, cityCode, cityName.toCopy(), requirementVersionId, requirementVersion,
        status, optimisticVersion, submittedAt, reviewedAt, updatedAt, latestApplicantMessage,
    )
}

@Serializable
private data class ApplicationAnswerDto(
    @SerialName("requirement_item_id") val requirementItemId: String,
    @SerialName("answer_type") val answerType: String,
    @SerialName("boolean_value") val booleanValue: Boolean? = null,
    @SerialName("date_value") val dateValue: String? = null,
    @SerialName("text_value") val textValue: String? = null,
) {
    fun toDomain() = DriverApplicationAnswer(requirementItemId, answerType, booleanValue, dateValue, textValue)
}

@Serializable
private data class ApplicationEvidenceDto(
    @SerialName("requirement_item_id") val requirementItemId: String,
    @SerialName("evidence_type") val evidenceType: String,
    @SerialName("profile_id") val profileId: String? = null,
    @SerialName("vehicle_id") val vehicleId: String? = null,
    @SerialName("credential_id") val credentialId: String? = null,
    @SerialName("document_id") val documentId: String? = null,
    val status: String,
) {
    fun toDomain() = DriverApplicationEvidence(
        requirementItemId, DriverRequirementEvidenceType.valueOf(evidenceType), profileId,
        vehicleId, credentialId, documentId, status,
    )
}

@Serializable
private data class ApplicationDocumentDto(
    val id: String,
    @SerialName("requirement_item_id") val requirementItemId: String,
    @SerialName("media_type") val mediaType: String,
    @SerialName("byte_size") val byteSize: Long,
    @SerialName("scan_status") val scanStatus: String,
    @SerialName("uploaded_at") val uploadedAt: String,
    @SerialName("deleted_at") val deletedAt: String? = null,
) {
    fun toDomain() = DriverApplicationDocument(
        id, requirementItemId, mediaType, byteSize, scanStatus, uploadedAt, deletedAt,
    )
}

@Serializable
private data class ApplicantDecisionDto(
    val decision: String,
    @SerialName("reason_code") val reasonCode: String,
    val message: String,
    @SerialName("created_at") val createdAt: String,
) {
    fun toDomain() = ApplicantDecision(decision, reasonCode, message, createdAt)
}

@Serializable
private data class AuthorizationDto(
    val id: String,
    @SerialName("city_id") val cityId: String,
    val status: String,
    @SerialName("vehicle_id") val vehicleId: String? = null,
    @SerialName("service_types") val serviceTypes: List<String>,
    @SerialName("scheduled_offers_enabled") val scheduledOffersEnabled: Boolean,
    @SerialName("valid_from") val validFrom: String,
    @SerialName("valid_until") val validUntil: String? = null,
) {
    fun toDomain() = DriverCityAuthorization(
        id, cityId, status, vehicleId, serviceTypes, scheduledOffersEnabled, validFrom, validUntil,
    )
}

@Serializable
private data class CityApplicationDto(
    val id: String,
    @SerialName("driver_id") val driverId: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("city_code") val cityCode: String,
    @SerialName("city_name") val cityName: Map<String, String>,
    @SerialName("requirement_version_id") val requirementVersionId: String,
    @SerialName("requirement_version") val requirementVersion: String,
    val status: String,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("submission_revision") val submissionRevision: Int,
    val editable: Boolean,
    val complete: Boolean,
    @SerialName("missing_required_item_ids") val missingRequiredItemIds: List<String>,
    @SerialName("document_upload_available") val documentUploadAvailable: Boolean,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("reviewed_at") val reviewedAt: String? = null,
    @SerialName("withdrawn_at") val withdrawnAt: String? = null,
    @SerialName("updated_at") val updatedAt: String,
    val requirements: List<RequirementDto>,
    val answers: List<ApplicationAnswerDto>,
    val evidence: List<ApplicationEvidenceDto>,
    val documents: List<ApplicationDocumentDto>,
    @SerialName("latest_decision") val latestDecision: ApplicantDecisionDto? = null,
    val authorization: AuthorizationDto? = null,
) {
    fun toDomain() = DriverCityApplication(
        id = id,
        driverId = driverId,
        cityId = cityId,
        cityCode = cityCode,
        cityName = cityName.toCopy(),
        requirementVersionId = requirementVersionId,
        requirementVersion = requirementVersion,
        status = status,
        optimisticVersion = optimisticVersion,
        submissionRevision = submissionRevision,
        editable = editable,
        complete = complete,
        missingRequiredItemIds = missingRequiredItemIds.toSet(),
        documentUploadAvailable = documentUploadAvailable,
        submittedAt = submittedAt,
        reviewedAt = reviewedAt,
        withdrawnAt = withdrawnAt,
        updatedAt = updatedAt,
        requirements = requirements.map(RequirementDto::toDomain),
        answers = answers.map(ApplicationAnswerDto::toDomain),
        evidence = evidence.map(ApplicationEvidenceDto::toDomain),
        documents = documents.map(ApplicationDocumentDto::toDomain),
        latestDecision = latestDecision?.toDomain(),
        authorization = authorization?.toDomain(),
    )
}

@Serializable
private data class CreateCityApplicationDto(
    @SerialName("city_id") val cityId: String,
    @SerialName("display_name") val displayName: String? = null,
)

@Serializable
private data class UpdateCityApplicationDto(
    @SerialName("expected_version") val expectedVersion: Int,
    val answers: List<ApplicationAnswerDraftDto>? = null,
    val evidence: List<ApplicationEvidenceDraftDto>? = null,
    @SerialName("remove_answer_item_ids") val removeAnswerItemIds: List<String> = emptyList(),
    @SerialName("remove_evidence_item_ids") val removeEvidenceItemIds: List<String> = emptyList(),
)

@Serializable
private data class ApplicationAnswerDraftDto(
    @SerialName("requirement_item_id") val requirementItemId: String,
    @SerialName("answer_type") val answerType: String,
    @SerialName("boolean_value") val booleanValue: Boolean? = null,
    @SerialName("date_value") val dateValue: String? = null,
    @SerialName("text_value") val textValue: String? = null,
) {
    companion object {
        fun from(value: DriverApplicationAnswerDraft) = ApplicationAnswerDraftDto(
            value.requirementItemId, value.answerType, value.booleanValue, value.dateValue, value.textValue,
        )
    }
}

@Serializable
private data class ApplicationEvidenceDraftDto(
    @SerialName("requirement_item_id") val requirementItemId: String,
    @SerialName("profile_id") val profileId: String? = null,
    @SerialName("vehicle_id") val vehicleId: String? = null,
    @SerialName("credential_id") val credentialId: String? = null,
) {
    companion object {
        fun from(value: DriverApplicationEvidenceDraft) = ApplicationEvidenceDraftDto(
            value.requirementItemId, value.profileId, value.vehicleId, value.credentialId,
        )
    }
}

private fun Map<String, String>.toCopy() = RecruitmentCopy(
    english = get("en").orEmpty(),
    french = get("fr") ?: get("en").orEmpty(),
    arabic = get("ar") ?: get("en").orEmpty(),
)
