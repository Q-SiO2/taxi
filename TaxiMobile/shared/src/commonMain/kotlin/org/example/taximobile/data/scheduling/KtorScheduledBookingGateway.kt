package org.example.taximobile.data.scheduling

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
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
import org.example.taximobile.data.network.newIdempotencyKey
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.scheduling.ScheduledBooking
import org.example.taximobile.domain.scheduling.ScheduledBookingEstimate
import org.example.taximobile.domain.scheduling.ScheduledBookingGateway
import org.example.taximobile.domain.scheduling.ScheduledCancellationTerms
import org.example.taximobile.domain.scheduling.ScheduledCommitment
import org.example.taximobile.domain.scheduling.ScheduledEconomics
import org.example.taximobile.domain.scheduling.ScheduledOffer
import org.example.taximobile.domain.scheduling.ScheduledOfferPreference

class KtorScheduledBookingGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : ScheduledBookingGateway {
    override suspend fun passengerBookings(): List<ScheduledBooking> = request {
        val response = client.get(api.endpoint("scheduled-bookings")) { authorize() }
        response.requireSuccess("load scheduled bookings")
        response.body<ScheduledBookingListResponse>().items.map(ScheduledBookingResponse::toDomain)
    }

    override suspend fun estimatePointToPoint(
        scheduledFor: String,
        cityId: String?,
        pickup: Coordinates,
        destination: Coordinates,
    ): ScheduledBookingEstimate = estimate(
        ScheduledBookingCreateRequest(
            scheduledFor = scheduledFor,
            cityId = cityId,
            pickup = pickup.toResponse(),
            destination = destination.toResponse(),
        ),
    )

    override suspend fun estimateFixedRoute(
        scheduledFor: String,
        directionVersionId: String,
    ): ScheduledBookingEstimate = estimate(
        ScheduledBookingCreateRequest(
            scheduledFor = scheduledFor,
            fixedRouteDirectionVersionId = directionVersionId,
        ),
    )

    private suspend fun estimate(payload: ScheduledBookingCreateRequest): ScheduledBookingEstimate = request {
        val response = client.post(api.endpoint("scheduled-bookings/estimate")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(payload)
        }
        response.requireSuccess("estimate this scheduled booking")
        response.body<ScheduledBookingEstimateResponse>().toDomain()
    }

    override suspend fun createPointToPoint(
        scheduledFor: String,
        cityId: String?,
        pickup: Coordinates,
        destination: Coordinates,
        passengerNote: String?,
        reviewedEconomics: ScheduledEconomics,
    ): ScheduledBooking = create(
        ScheduledBookingCreateRequest(
            scheduledFor = scheduledFor,
            cityId = cityId,
            pickup = pickup.toResponse(),
            destination = destination.toResponse(),
            passengerNote = passengerNote?.trim()?.ifBlank { null },
            expectedPricingRuleVersion = reviewedEconomics.pricingRuleVersion,
            expectedOperatorFeePolicyVersion = reviewedEconomics.operatorFeePolicyVersion,
            expectedSchedulingPolicyVersion = reviewedEconomics.schedulingPolicyVersion,
        ),
    )

    override suspend fun createFixedRoute(
        scheduledFor: String,
        directionVersionId: String,
        passengerNote: String?,
        reviewedEconomics: ScheduledEconomics,
    ): ScheduledBooking = create(
        ScheduledBookingCreateRequest(
            scheduledFor = scheduledFor,
            fixedRouteDirectionVersionId = directionVersionId,
            passengerNote = passengerNote?.trim()?.ifBlank { null },
            expectedPricingRuleVersion = reviewedEconomics.pricingRuleVersion,
            expectedOperatorFeePolicyVersion = reviewedEconomics.operatorFeePolicyVersion,
            expectedSchedulingPolicyVersion = reviewedEconomics.schedulingPolicyVersion,
        ),
    )

    private suspend fun create(payload: ScheduledBookingCreateRequest): ScheduledBooking {
        val key = newIdempotencyKey()
        return idempotentRequest {
            val response = client.post(api.endpoint("scheduled-bookings")) {
                authorize()
                header("Idempotency-Key", key)
                contentType(ContentType.Application.Json)
                setBody(payload)
            }
            response.requireSuccess("create this scheduled booking")
            response.body<ScheduledBookingResponse>().toDomain()
        }
    }

    override suspend fun cancelPassengerBooking(bookingId: String, reason: String): ScheduledBooking {
        val key = newIdempotencyKey()
        return idempotentRequest {
            val response = client.post(api.endpoint("scheduled-bookings/$bookingId/cancel")) {
                authorize()
                header("Idempotency-Key", key)
                contentType(ContentType.Application.Json)
                setBody(ScheduledCancelRequest(reason.trim()))
            }
            response.requireSuccess("cancel this scheduled booking")
            response.body<ScheduledBookingResponse>().toDomain()
        }
    }

    override suspend fun driverOffers(): List<ScheduledOffer> = request {
        val response = client.get(api.endpoint("drivers/me/scheduled-offers")) { authorize() }
        response.requireSuccess("load scheduled offers")
        response.body<ScheduledOfferListResponse>().items.map(ScheduledOfferResponse::toDomain)
    }

    override suspend fun driverCommitments(): List<ScheduledCommitment> = request {
        val response = client.get(api.endpoint("drivers/me/scheduled-commitments")) { authorize() }
        response.requireSuccess("load scheduled commitments")
        response.body<ScheduledCommitmentListResponse>().items.map(ScheduledCommitmentResponse::toDomain)
    }

    override suspend fun driverPreferences(): List<ScheduledOfferPreference> = request {
        val response = client.get(api.endpoint("drivers/me/scheduled-offer-preferences")) { authorize() }
        response.requireSuccess("load scheduled-offer preferences")
        response.body<ScheduledPreferenceListResponse>().items.map(ScheduledPreferenceResponse::toDomain)
    }

    override suspend fun setDriverPreference(cityId: String, enabled: Boolean): ScheduledOfferPreference = request {
        val response = client.patch(api.endpoint("drivers/me/scheduled-offer-preference")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(ScheduledPreferenceRequest(cityId, enabled))
        }
        response.requireSuccess("update the scheduled-offer preference")
        response.body<ScheduledPreferenceResponse>().toDomain()
    }

    override suspend fun acceptOffer(offerId: String): ScheduledCommitment = request {
        val response = client.post(api.endpoint("scheduled-offers/$offerId/accept")) { authorize() }
        response.requireSuccess("accept this scheduled offer")
        response.body<ScheduledCommitmentResponse>().toDomain()
    }

    override suspend fun declineOffer(offerId: String, reason: String?): ScheduledOffer = request {
        val response = client.post(api.endpoint("scheduled-offers/$offerId/decline")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(ScheduledDeclineRequest(reason?.trim()?.ifBlank { null }))
        }
        response.requireSuccess("decline this scheduled offer")
        response.body<ScheduledOfferResponse>().toDomain()
    }

    private suspend fun io.ktor.client.request.HttpRequestBuilder.authorize() {
        header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
    }

    private fun io.ktor.client.statement.HttpResponse.requireSuccess(action: String) {
        if (status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!status.isSuccess()) throw ApiRequestException(status.value, "The server could not $action.")
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

    private suspend fun <T> idempotentRequest(block: suspend () -> T): T = try {
        block()
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (_: Exception) {
        try {
            block()
        } catch (error: AuthenticationRejectedException) {
            throw error
        } catch (error: ApiRequestException) {
            throw error
        } catch (_: Exception) {
            throw AuthenticationNetworkException()
        }
    }
}

@Serializable
internal data class CoordinateResponse(val latitude: Double, val longitude: Double, val address: String? = null)
private fun Coordinates.toResponse() = CoordinateResponse(latitude, longitude, address)
private fun CoordinateResponse.toDomain() = Coordinates(latitude, longitude, address)

@Serializable
internal data class ScheduledEconomicsResponse(
    @SerialName("transport_fare") val transportFare: String,
    @SerialName("scheduling_surcharge") val schedulingSurcharge: String,
    @SerialName("operator_service_fee") val operatorServiceFee: String,
    @SerialName("passenger_total") val passengerTotal: String,
    @SerialName("expected_driver_net") val expectedDriverNet: String,
    @SerialName("operator_allocation") val operatorAllocation: String,
    val currency: String,
    @SerialName("pricing_rule_version") val pricingRuleVersion: String,
    @SerialName("operator_fee_policy_version") val operatorFeePolicyVersion: String,
    @SerialName("scheduling_policy_version") val schedulingPolicyVersion: String,
)
private fun ScheduledEconomicsResponse.toDomain() = ScheduledEconomics(
    transportFare, schedulingSurcharge, operatorServiceFee, passengerTotal,
    expectedDriverNet, operatorAllocation, currency, pricingRuleVersion,
    operatorFeePolicyVersion, schedulingPolicyVersion,
)

@Serializable
internal data class ScheduledCancellationTermsResponse(
    @SerialName("passenger_cancel_cutoff_minutes") val passengerCancelCutoffMinutes: Int,
    @SerialName("surcharge_refund_mode") val surchargeRefundMode: String,
    val summary: String,
)
private fun ScheduledCancellationTermsResponse.toDomain() = ScheduledCancellationTerms(
    passengerCancelCutoffMinutes, surchargeRefundMode, summary,
)

@Serializable
internal data class ScheduledBookingResponse(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    @SerialName("service_type") val serviceType: String,
    @SerialName("fixed_route_direction_version_id") val fixedRouteDirectionVersionId: String? = null,
    @SerialName("scheduled_for") val scheduledFor: String,
    @SerialName("city_timezone") val cityTimezone: String,
    val status: String,
    val pickup: CoordinateResponse,
    val destination: CoordinateResponse,
    val economics: ScheduledEconomicsResponse,
    @SerialName("cancellation_terms") val cancellationTerms: ScheduledCancellationTermsResponse,
    @SerialName("driver_committed") val driverCommitted: Boolean,
    @SerialName("live_ride_id") val liveRideId: String? = null,
    @SerialName("cancellation_financial_outcome") val cancellationFinancialOutcome: String? = null,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
internal data class ScheduledBookingEstimateResponse(
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    @SerialName("service_type") val serviceType: String,
    @SerialName("fixed_route_direction_version_id") val fixedRouteDirectionVersionId: String? = null,
    @SerialName("scheduled_for") val scheduledFor: String,
    @SerialName("city_timezone") val cityTimezone: String,
    val pickup: CoordinateResponse,
    val destination: CoordinateResponse,
    val economics: ScheduledEconomicsResponse,
    @SerialName("cancellation_terms") val cancellationTerms: ScheduledCancellationTermsResponse,
    @SerialName("payment_method") val paymentMethod: String,
)
internal fun ScheduledBookingEstimateResponse.toDomain() = ScheduledBookingEstimate(
    cityId, operatorId, serviceType, fixedRouteDirectionVersionId, scheduledFor,
    cityTimezone, pickup.toDomain(), destination.toDomain(), economics.toDomain(),
    cancellationTerms.toDomain(), paymentMethod,
)
internal fun ScheduledBookingResponse.toDomain() = ScheduledBooking(
    id, cityId, operatorId, serviceType, fixedRouteDirectionVersionId, scheduledFor,
    cityTimezone, status, pickup.toDomain(), destination.toDomain(), economics.toDomain(),
    cancellationTerms.toDomain(), driverCommitted, liveRideId, cancellationFinancialOutcome, createdAt,
)

@Serializable internal data class ScheduledBookingListResponse(val items: List<ScheduledBookingResponse>)

@Serializable
internal data class ScheduledOfferResponse(
    val id: String,
    @SerialName("booking_id") val bookingId: String,
    val status: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("service_type") val serviceType: String,
    @SerialName("scheduled_for") val scheduledFor: String,
    @SerialName("city_timezone") val cityTimezone: String,
    @SerialName("expires_at") val expiresAt: String,
    val pickup: CoordinateResponse,
    val destination: CoordinateResponse,
    val economics: ScheduledEconomicsResponse,
    @SerialName("cancellation_terms") val cancellationTerms: ScheduledCancellationTermsResponse,
    @SerialName("server_time") val serverTime: String,
)
internal fun ScheduledOfferResponse.toDomain() = ScheduledOffer(
    id, bookingId, status, cityId, serviceType, scheduledFor, cityTimezone, expiresAt,
    pickup.toDomain(), destination.toDomain(), economics.toDomain(), cancellationTerms.toDomain(), serverTime,
)
@Serializable internal data class ScheduledOfferListResponse(val items: List<ScheduledOfferResponse>)

@Serializable
internal data class ScheduledCommitmentResponse(
    val id: String,
    @SerialName("booking_id") val bookingId: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("service_type") val serviceType: String,
    @SerialName("scheduled_for") val scheduledFor: String,
    @SerialName("city_timezone") val cityTimezone: String,
    val status: String,
    @SerialName("protected_from") val protectedFrom: String,
    @SerialName("protected_until") val protectedUntil: String,
    val pickup: CoordinateResponse,
    val destination: CoordinateResponse,
    val economics: ScheduledEconomicsResponse,
)
internal fun ScheduledCommitmentResponse.toDomain() = ScheduledCommitment(
    id, bookingId, cityId, serviceType, scheduledFor, cityTimezone, status,
    protectedFrom, protectedUntil, pickup.toDomain(), destination.toDomain(), economics.toDomain(),
)
@Serializable internal data class ScheduledCommitmentListResponse(val items: List<ScheduledCommitmentResponse>)

@Serializable
private data class ScheduledBookingCreateRequest(
    @SerialName("scheduled_for") val scheduledFor: String,
    @SerialName("city_id") val cityId: String? = null,
    val pickup: CoordinateResponse? = null,
    val destination: CoordinateResponse? = null,
    @SerialName("fixed_route_direction_version_id") val fixedRouteDirectionVersionId: String? = null,
    @SerialName("passenger_note") val passengerNote: String? = null,
    @SerialName("payment_method") val paymentMethod: String = "CASH",
    @SerialName("expected_pricing_rule_version") val expectedPricingRuleVersion: String? = null,
    @SerialName("expected_operator_fee_policy_version") val expectedOperatorFeePolicyVersion: String? = null,
    @SerialName("expected_scheduling_policy_version") val expectedSchedulingPolicyVersion: String? = null,
)
@Serializable private data class ScheduledCancelRequest(val reason: String)
@Serializable private data class ScheduledDeclineRequest(val reason: String? = null)
@Serializable private data class ScheduledPreferenceRequest(@SerialName("city_id") val cityId: String, val enabled: Boolean)
@Serializable internal data class ScheduledPreferenceResponse(@SerialName("city_id") val cityId: String, val enabled: Boolean, @SerialName("updated_at") val updatedAt: String)
@Serializable internal data class ScheduledPreferenceListResponse(val items: List<ScheduledPreferenceResponse>)
internal fun ScheduledPreferenceResponse.toDomain() = ScheduledOfferPreference(cityId, enabled, updatedAt)
