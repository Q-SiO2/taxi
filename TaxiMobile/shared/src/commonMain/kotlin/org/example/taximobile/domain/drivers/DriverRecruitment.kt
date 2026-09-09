package org.example.taximobile.domain.drivers

/** Backend-localized copy retained as data so the active app locale chooses presentation. */
data class RecruitmentCopy(
    val english: String,
    val french: String,
    val arabic: String,
) {
    fun forLanguage(language: String): String = when (language.lowercase()) {
        "ar" -> arabic
        "fr" -> french
        else -> english
    }
}

data class RecruitingCity(
    val id: String,
    val code: String,
    val name: RecruitmentCopy,
    val timezone: String,
    val lifecycleStatus: String,
    val requirementVersionId: String,
    val requirementVersion: String,
)

enum class DriverRequirementEvidenceType {
    PROFILE,
    VEHICLE,
    CREDENTIAL,
    DOCUMENT,
    BOOLEAN,
    DATE,
    TEXT,
}

data class DriverRequirement(
    val id: String,
    val code: String,
    val evidenceType: DriverRequirementEvidenceType,
    val required: Boolean,
    val validityRule: String,
    val referenceType: String?,
    val displayOrder: Int,
    val label: RecruitmentCopy,
    val description: RecruitmentCopy,
)

data class DriverApplicationAnswer(
    val requirementItemId: String,
    val answerType: String,
    val booleanValue: Boolean? = null,
    val dateValue: String? = null,
    val textValue: String? = null,
)

data class DriverApplicationEvidence(
    val requirementItemId: String,
    val evidenceType: DriverRequirementEvidenceType,
    val profileId: String? = null,
    val vehicleId: String? = null,
    val credentialId: String? = null,
    val documentId: String? = null,
    val status: String,
)

data class DriverApplicationDocument(
    val id: String,
    val requirementItemId: String,
    val mediaType: String,
    val byteSize: Long,
    val scanStatus: String,
    val uploadedAt: String,
    val deletedAt: String?,
)

data class DriverDocumentUpload(
    val fileName: String,
    val mediaType: String,
    val bytes: ByteArray,
)

data class ApplicantDecision(
    val decision: String,
    val reasonCode: String,
    val message: String,
    val createdAt: String,
)

data class DriverCityAuthorization(
    val id: String,
    val cityId: String,
    val status: String,
    val vehicleId: String?,
    val serviceTypes: List<String>,
    val scheduledOffersEnabled: Boolean,
    val validFrom: String,
    val validUntil: String?,
)

/** A display-safe city label paired with the backend-issued operating authority. */
data class DriverAuthorizedMarket(
    val applicationId: String,
    val cityId: String,
    val cityCode: String,
    val cityName: RecruitmentCopy,
    val authorization: DriverCityAuthorization,
)

data class DriverCityApplicationSummary(
    val id: String,
    val cityId: String,
    val cityCode: String,
    val cityName: RecruitmentCopy,
    val requirementVersionId: String,
    val requirementVersion: String,
    val status: String,
    val optimisticVersion: Int,
    val submittedAt: String?,
    val reviewedAt: String?,
    val updatedAt: String,
    val latestApplicantMessage: String?,
)

data class DriverCityApplication(
    val id: String,
    val driverId: String,
    val cityId: String,
    val cityCode: String,
    val cityName: RecruitmentCopy,
    val requirementVersionId: String,
    val requirementVersion: String,
    val status: String,
    val optimisticVersion: Int,
    val submissionRevision: Int,
    val editable: Boolean,
    val complete: Boolean,
    val missingRequiredItemIds: Set<String>,
    val documentUploadAvailable: Boolean,
    val submittedAt: String?,
    val reviewedAt: String?,
    val withdrawnAt: String?,
    val updatedAt: String,
    val requirements: List<DriverRequirement>,
    val answers: List<DriverApplicationAnswer>,
    val evidence: List<DriverApplicationEvidence>,
    val documents: List<DriverApplicationDocument>,
    val latestDecision: ApplicantDecision?,
    val authorization: DriverCityAuthorization?,
)

data class DriverApplicationAnswerDraft(
    val requirementItemId: String,
    val answerType: String,
    val booleanValue: Boolean? = null,
    val dateValue: String? = null,
    val textValue: String? = null,
)

data class DriverApplicationEvidenceDraft(
    val requirementItemId: String,
    val profileId: String? = null,
    val vehicleId: String? = null,
    val credentialId: String? = null,
)

interface DriverRecruitmentGateway {
    suspend fun recruitingCities(): List<RecruitingCity>
    suspend fun applications(): List<DriverCityApplicationSummary>
    suspend fun application(applicationId: String): DriverCityApplication
    suspend fun createApplication(cityId: String, displayName: String?): DriverCityApplication
    suspend fun updateApplication(
        applicationId: String,
        expectedVersion: Int,
        answers: List<DriverApplicationAnswerDraft> = emptyList(),
        evidence: List<DriverApplicationEvidenceDraft> = emptyList(),
        removeAnswerItemIds: List<String> = emptyList(),
        removeEvidenceItemIds: List<String> = emptyList(),
    ): DriverCityApplication
    suspend fun submitApplication(applicationId: String): DriverCityApplication
    suspend fun withdrawApplication(applicationId: String): DriverCityApplication
    suspend fun uploadDocument(
        applicationId: String,
        requirementItemId: String,
        expectedVersion: Int,
        document: DriverDocumentUpload,
    ): DriverCityApplication
    suspend fun deleteDocument(
        applicationId: String,
        documentId: String,
        expectedVersion: Int,
    ): DriverCityApplication
}
