package org.example.taximobile.operations.model

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlin.time.Instant
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

class StaffAccessModelsTest {
    private val now = Instant.parse("2026-09-03T12:00:00Z")
    private val currentUserId = "7f5b1477-0773-4a3c-80ef-ae7a4db56fa7"
    private val targetUserId = "eef3fa3a-5740-4b47-a22b-b4638a0870fa"
    private val marketId = "dd38d7e4-8b9f-4c02-82cc-7d0c733a11e7"
    private val operatorId = "ccf91283-4ab1-4dc2-ae66-5071cbde3c62"
    private val cityId = "b3f878e4-cf9f-4b82-97cc-c50483925582"

    @Test
    fun role_templates_have_one_documented_scope_kind() {
        assertEquals(9, ADMINISTRATIVE_ROLE_TEMPLATES.size)
        assertEquals(
            AdministrativeGrantScopeKind.MARKET,
            administrativeRoleTemplate("PLATFORM_ADMIN")?.scopeKind,
        )
        assertEquals(
            AdministrativeGrantScopeKind.OPERATOR,
            administrativeRoleTemplate("OPERATOR_ADMIN")?.scopeKind,
        )
        assertTrue(
            ADMINISTRATIVE_ROLE_TEMPLATES
                .filter { it.value !in setOf("PLATFORM_ADMIN", "OPERATOR_ADMIN") }
                .all { it.scopeKind == AdministrativeGrantScopeKind.CITY },
        )
    }

    @Test
    fun valid_bounded_city_grant_matches_only_the_selected_city() {
        val request = AdministrativeGrantCreateRequest(
            userId = targetUserId,
            roleTemplate = "SAFETY_RESPONDER",
            cityId = cityId,
            expiresAt = "2026-12-31T23:59:59Z",
            reason = "Approved safety rota access",
        )

        assertNull(administrativeGrantInputError(request, currentUserId, now))
        assertTrue(request.matchesSelectedScope(OperationsScope(marketId = marketId, cityId = cityId)))
        assertFalse(request.matchesSelectedScope(OperationsScope(marketId = marketId, cityId = operatorId)))
    }

    @Test
    fun validation_rejects_self_grant_scope_mismatch_and_past_expiry() {
        val selfGrant = AdministrativeGrantCreateRequest(
            userId = currentUserId,
            roleTemplate = "PLATFORM_ADMIN",
            marketId = marketId,
            reason = "Attempted self extension",
        )
        assertTrue(
            administrativeGrantInputError(selfGrant, currentUserId, now)!!.contains("own account"),
        )

        val mismatched = selfGrant.copy(
            userId = targetUserId,
            marketId = null,
            cityId = cityId,
        )
        assertTrue(
            administrativeGrantInputError(mismatched, currentUserId, now)!!.contains("market scope"),
        )

        val expired = selfGrant.copy(
            userId = targetUserId,
            expiresAt = "2026-09-03T11:59:59Z",
        )
        assertTrue(
            administrativeGrantInputError(expired, currentUserId, now)!!.contains("future"),
        )
    }

    @Test
    fun request_serialization_uses_backend_field_names_and_omits_other_scopes() {
        val request = AdministrativeGrantCreateRequest(
            userId = targetUserId,
            roleTemplate = "OPERATOR_ADMIN",
            operatorId = operatorId,
            reason = "Approved operator access",
        )
        val encoded = Json { explicitNulls = false }.encodeToString(request)

        assertTrue("\"user_id\":\"$targetUserId\"" in encoded)
        assertTrue("\"role_template\":\"OPERATOR_ADMIN\"" in encoded)
        assertTrue("\"operator_id\":\"$operatorId\"" in encoded)
        assertFalse("market_id" in encoded)
        assertFalse("city_id" in encoded)
    }

    @Test
    fun maker_and_target_cannot_decide_but_an_independent_admin_can() {
        val request = pendingRequest()

        assertTrue(
            administrativeGrantDecisionError(
                request,
                request.requesterUserId,
                "approve",
                "Independent review complete",
            )!!.contains("different accounts"),
        )
        assertTrue(
            administrativeGrantDecisionError(
                request,
                request.targetUserId,
                "reject",
                "Evidence was incomplete",
            )!!.contains("different accounts"),
        )
        assertNull(
            administrativeGrantDecisionError(
                request,
                currentUserId,
                "approve",
                "Independent review complete",
            ),
        )
    }

    @Test
    fun only_maker_can_cancel_and_terminal_requests_cannot_be_decided() {
        val request = pendingRequest()

        assertNull(
            administrativeGrantDecisionError(
                request,
                request.requesterUserId,
                "cancel",
                "Access request withdrawn",
            ),
        )
        assertTrue(
            administrativeGrantDecisionError(
                request,
                currentUserId,
                "cancel",
                "Attempted cancellation",
            )!!.contains("original requester"),
        )
        assertTrue(
            administrativeGrantDecisionError(
                request.copy(status = "APPROVED"),
                currentUserId,
                "approve",
                "Attempted replay",
            )!!.contains("pending"),
        )
    }

    @Test
    fun decision_payload_carries_optimistic_version_and_reason() {
        val encoded = Json.encodeToString(
            AdministrativeGrantDecisionRequest(
                expectedVersion = 4,
                reason = "Reviewed by the independent checker",
            )
        )

        assertTrue("\"expected_version\":4" in encoded)
        assertTrue("\"reason\":\"Reviewed by the independent checker\"" in encoded)
    }

    private fun pendingRequest() = AdministrativeGrantChangeRequestRecord(
        id = "e559527d-7daf-4373-a79e-808c451ac62c",
        action = "CREATE",
        status = "PENDING",
        requesterUserId = "81269956-55f3-4dfe-9b7c-eb408ec41fbf",
        targetUserId = targetUserId,
        roleTemplate = "CITY_MANAGER",
        cityId = cityId,
        reason = "Reviewed city duty assignment",
        requestedAt = "2026-09-03T12:00:00Z",
        optimisticVersion = 1,
    )
}
