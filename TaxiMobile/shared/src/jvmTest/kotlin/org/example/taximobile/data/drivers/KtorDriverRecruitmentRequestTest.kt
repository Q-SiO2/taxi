package org.example.taximobile.data.drivers

import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpMethod
import io.ktor.http.HttpStatusCode
import io.ktor.http.content.OutgoingContent
import io.ktor.http.headersOf
import io.ktor.utils.io.ByteReadChannel
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.data.network.TaxiMobileClientIdentity
import org.example.taximobile.data.network.TaxiMobileClientSurface
import org.example.taximobile.data.network.configureTaxiMobileTransport
import org.example.taximobile.domain.drivers.DriverApplicationAnswerDraft
import org.example.taximobile.domain.drivers.DriverApplicationEvidenceDraft
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertIs
import kotlin.test.assertTrue

class KtorDriverRecruitmentRequestTest {
    @Test
    fun profileOnlySaveSendsExplicitEmptyPatchesAndReadsServerVersion() = runBlocking {
        withGateway { gateway, engine ->
            val saved = gateway.updateApplication(APPLICATION_ID, 1, emptyList(), emptyList(), emptyList(), emptyList())
            val request = engine.requestHistory.single()
            assertEquals(HttpMethod.Patch, request.method)
            assertEquals("/api/v1/drivers/me/city-applications/$APPLICATION_ID", request.url.encodedPath)
            assertEquals("Bearer synthetic-test-token", request.headers[HttpHeaders.Authorization])
            assertEquals("WEB_APPLICANT", request.headers["X-TaxiMobile-Client"])
            assertEquals("1.0.0", request.headers["X-TaxiMobile-Version"])
            assertEquals("1", request.headers["X-TaxiMobile-Build"])
            val body = Json.parseToJsonElement(
                assertIs<OutgoingContent.ByteArrayContent>(request.body).bytes().decodeToString(),
            ).jsonObject
            assertEquals("1", body.getValue("expected_version").jsonPrimitive.content)
            assertEquals(emptyList(), body.getValue("answers").jsonArray.toList())
            assertEquals(emptyList(), body.getValue("evidence").jsonArray.toList())
            assertEquals(2, saved.optimisticVersion)
            assertEquals("NOT_STARTED", saved.status)
            assertTrue(saved.complete)
            assertEquals(PROFILE_ID, saved.evidence.single().profileId)
        }
    }

    @Test
    fun typedUpdatesAndExplicitRemovalsKeepThePatchContract() = runBlocking {
        withGateway { gateway, engine ->
            gateway.updateApplication(
                APPLICATION_ID, 1,
                listOf(DriverApplicationAnswerDraft("text-item", "TEXT", textValue = "مراجعة")),
                listOf(DriverApplicationEvidenceDraft("profile-item", profileId = PROFILE_ID)),
                listOf("removed-answer"), listOf("removed-evidence"),
            )
            val body = Json.parseToJsonElement(
                assertIs<OutgoingContent.ByteArrayContent>(engine.requestHistory.single().body).bytes().decodeToString(),
            ).jsonObject
            val answer = body.getValue("answers").jsonArray.single().jsonObject
            assertEquals("text-item", answer.getValue("requirement_item_id").jsonPrimitive.content)
            assertEquals("TEXT", answer.getValue("answer_type").jsonPrimitive.content)
            assertEquals("مراجعة", answer.getValue("text_value").jsonPrimitive.content)
            val evidence = body.getValue("evidence").jsonArray.single().jsonObject
            assertEquals(PROFILE_ID, evidence.getValue("profile_id").jsonPrimitive.content)
            assertEquals("profile-item", evidence.getValue("requirement_item_id").jsonPrimitive.content)
            assertEquals("removed-answer", body.getValue("remove_answer_item_ids").jsonArray.single().jsonPrimitive.content)
            assertEquals("removed-evidence", body.getValue("remove_evidence_item_ids").jsonArray.single().jsonPrimitive.content)
        }
    }

    @Test
    fun conflictStaysAnErrorWithoutAnAutomaticRetry() = runBlocking {
        withGateway(HttpStatusCode.Conflict) { gateway, engine ->
            val failure = assertFailsWith<ApiRequestException> {
                gateway.updateApplication(APPLICATION_ID, 1, emptyList(), emptyList(), emptyList(), emptyList())
            }
            assertEquals(409, failure.statusCode)
            assertEquals(1, engine.requestHistory.size)
        }
    }

    private suspend fun withGateway(
        status: HttpStatusCode = HttpStatusCode.OK,
        block: suspend (KtorDriverRecruitmentGateway, MockEngine) -> Unit,
    ) {
        val engine = MockEngine {
            respond(ByteReadChannel(RESPONSE), status, headersOf(HttpHeaders.ContentType, "application/json"))
        }
        val client = HttpClient(engine) {
            configureTaxiMobileTransport(TaxiMobileClientIdentity(TaxiMobileClientSurface.WEB_APPLICANT, "1.0.0", "1"))
        }
        try {
            block(KtorDriverRecruitmentGateway(client, ApiConfiguration("https://synthetic.example")) {
                "synthetic-test-token"
            }, engine)
        } finally {
            client.close()
            engine.close()
        }
    }

    private companion object {
        const val APPLICATION_ID = "10000000-0000-4000-8000-000000000001"
        const val PROFILE_ID = "20000000-0000-4000-8000-000000000001"
        val RESPONSE = """
            {
              "id":"$APPLICATION_ID", "driver_id":"$PROFILE_ID",
              "city_id":"30000000-0000-4000-8000-000000000001", "city_code":"CASABLANCA",
              "city_name":{"en":"Casablanca","fr":"Casablanca","ar":"الدار البيضاء"},
              "requirement_version_id":"40000000-0000-4000-8000-000000000001",
              "requirement_version":"legacy-compatibility-v1", "status":"NOT_STARTED",
              "optimistic_version":2, "submission_revision":0, "editable":true, "complete":true,
              "missing_required_item_ids":[], "document_upload_available":false,
              "updated_at":"2026-10-18T15:00:00Z",
              "requirements":[{
                "id":"profile-item", "requirement_code":"PROFILE", "evidence_type":"PROFILE",
                "required":true, "validity_rule_code":"EXISTS", "display_order":0,
                "localized_label":{"en":"Profile","fr":"Profil","ar":"الملف"},
                "localized_description":{"en":"Your profile","fr":"Votre profil","ar":"ملفك"}
              }],
              "answers":[], "documents":[],
              "evidence":[{"requirement_item_id":"profile-item", "evidence_type":"PROFILE",
                "profile_id":"$PROFILE_ID", "status":"LINKED"}]
            }
        """.trimIndent()
    }
}
