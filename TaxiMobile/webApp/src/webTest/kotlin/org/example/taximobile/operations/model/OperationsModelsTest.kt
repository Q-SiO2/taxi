package org.example.taximobile.operations.model

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlinx.serialization.json.Json

class OperationsModelsTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun loginEnvelopeDistinguishesPasswordOnlyTokensFromMfaChallenge() {
        val tokens = json.decodeFromString<OperationsLoginEnvelope>(
            """{
                "access_token":"access",
                "refresh_token":"refresh",
                "token_type":"bearer",
                "expires_in":900,
                "authentication_strength":"PASSWORD_ONLY_LOCAL"
            }"""
        ).toLoginResult()
        val authenticated = assertIs<OperationsLoginResult.Authenticated>(tokens)
        assertEquals("access", authenticated.tokens.accessToken)
        assertEquals("PASSWORD_ONLY_LOCAL", authenticated.tokens.authenticationStrength)

        val challenge = json.decodeFromString<OperationsLoginEnvelope>(
            """{
                "challenge_id":"00000000-0000-0000-0000-000000000001",
                "expires_in":300,
                "authentication_methods":["TOTP","RECOVERY_CODE"]
            }"""
        ).toLoginResult()
        val mfa = assertIs<OperationsLoginResult.MfaRequired>(challenge)
        assertEquals(300, mfa.expiresIn)
        assertEquals(listOf("TOTP", "RECOVERY_CODE"), mfa.methods)
    }

    @Test
    fun stepUpEnvelopePreservesRecoveryCodeAuthenticationStrength() {
        val response = json.decodeFromString<OperationsMfaStepUpResponse>(
            """{
                "verified_at":"2026-08-30T20:00:00Z",
                "authentication_strength":"PASSWORD_RECOVERY_CODE_MFA"
            }"""
        )
        assertEquals("PASSWORD_RECOVERY_CODE_MFA", response.authenticationStrength)
    }

    @Test
    fun destinationsExposeOnlyImplementedModulesAllowedByPermissions() {
        assertEquals(
            listOf(
                OperationsDestination.ROLLOUT,
                OperationsDestination.CITIES,
                OperationsDestination.OPERATORS,
            ),
            availableDestinations(setOf(VIEW_CONTROL_PLANE)),
        )
        assertEquals(
            listOf(
                OperationsDestination.ROLLOUT,
                OperationsDestination.CITIES,
                OperationsDestination.OPERATORS,
                OperationsDestination.STAFF,
                OperationsDestination.AUDIT,
            ),
            availableDestinations(
                setOf(
                    VIEW_CONTROL_PLANE,
                    MANAGE_SCOPED_STAFF_GRANTS,
                    VIEW_SCOPED_AUDIT,
                )
            ),
        )
        assertEquals(
            listOf(
                OperationsDestination.DRIVER_RECRUITMENT,
                OperationsDestination.ANALYTICS,
            ),
            availableDestinations(setOf(VIEW_SCOPED_OPERATIONAL_AGGREGATES)),
        )
        assertEquals(
            listOf(
                OperationsDestination.ROLLOUT,
                OperationsDestination.CITIES,
                OperationsDestination.OPERATORS,
                OperationsDestination.DRIVER_RECRUITMENT,
            ),
            availableDestinations(setOf(VIEW_CONTROL_PLANE, REVIEW_DRIVER_APPLICATIONS)),
        )
        assertEquals(
            listOf(OperationsDestination.PRICING_ECONOMICS),
            availableDestinations(setOf(MANAGE_CITY_TARIFFS)),
        )
        assertEquals(
            listOf(OperationsDestination.FIXED_ROUTES),
            availableDestinations(setOf(MANAGE_FIXED_ROUTES)),
        )
        assertEquals(
            listOf(
                OperationsDestination.ROLLOUT,
                OperationsDestination.CITIES,
                OperationsDestination.OPERATORS,
                OperationsDestination.PRICING_ECONOMICS,
            ),
            availableDestinations(setOf(VIEW_CONTROL_PLANE, MANAGE_OPERATOR_FEE_POLICIES)),
        )
    }

    @Test
    fun lifecycleTargetsMatchTheDocumentedStateMachine() {
        assertEquals(listOf("CONFIGURING"), lifecycleTargetsFor("DRAFT"))
        assertEquals(listOf("PILOT"), lifecycleTargetsFor("CONFIGURING"))
        assertEquals(listOf("ACTIVE"), lifecycleTargetsFor("PILOT"))
        assertEquals(listOf("PAUSED", "RETIRED"), lifecycleTargetsFor("ACTIVE"))
        assertEquals(listOf("ACTIVE", "RETIRED"), lifecycleTargetsFor("PAUSED"))
        assertEquals(emptyList(), lifecycleTargetsFor("RETIRED"))
    }

    @Test
    fun readinessStagesDoNotTreatPilotAsPublicLaunch() {
        assertEquals(10, PILOT_ENTRY_READINESS_GATES.size)
        assertEquals(
            setOf("PILOT_SERVICE_AND_FAIRNESS"),
            PUBLIC_ACTIVATION_READINESS_GATES.toSet() - PILOT_ENTRY_READINESS_GATES.toSet(),
        )
        assertEquals("POST_LAUNCH_REVIEW", POST_LAUNCH_REVIEW_GATE)
    }
}
