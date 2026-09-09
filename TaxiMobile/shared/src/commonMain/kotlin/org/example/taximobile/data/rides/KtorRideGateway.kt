package org.example.taximobile.data.rides

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.header
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
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.data.network.newIdempotencyKey
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.AssignedDriver
import org.example.taximobile.domain.rides.AssignedVehicle
import org.example.taximobile.domain.rides.FareEstimate
import org.example.taximobile.domain.rides.FixedRouteCatalog
import org.example.taximobile.domain.rides.FixedRouteRideSummary
import org.example.taximobile.domain.rides.FareComponent
import org.example.taximobile.domain.rides.FareEconomics
import org.example.taximobile.domain.rides.FinalRideFare
import org.example.taximobile.domain.rides.LastKnownDriverLocation
import org.example.taximobile.domain.rides.ManualTransferInstructions
import org.example.taximobile.domain.rides.LocalizedText
import org.example.taximobile.domain.rides.PublicRideCity
import org.example.taximobile.domain.rides.PublishedFixedRouteDirection
import org.example.taximobile.domain.rides.PublishedFixedRouteStop
import org.example.taximobile.domain.rides.RideGateway
import org.example.taximobile.domain.rides.RideCoordinationCode
import org.example.taximobile.domain.rides.RideCoordinationMessage
import org.example.taximobile.domain.rides.RideCoordinationSenderRole
import org.example.taximobile.domain.rides.RidePaymentMethod
import org.example.taximobile.domain.rides.RideRating
import org.example.taximobile.domain.rides.RideReceipt
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.RideServiceType
import org.example.taximobile.domain.rides.RideSummary

class KtorRideGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : RideGateway {
    override suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): FareEstimate = request {
        val response = client.post(api.endpoint("rides/estimate")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(
                RideEstimateRequest(
                    pickup = pickup.toRequest(),
                    destination = destination.toRequest(),
                )
            )
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) {
            throw ApiRequestException(response.status.value, "The server could not estimate this ride.")
        }
        val body = response.body<RideEstimateResponse>()
        val methods = body.paymentMethods.mapNotNull { value ->
            when (value) {
                RidePaymentMethod.CASH.name -> RidePaymentMethod.CASH
                RidePaymentMethod.MANUAL_TRANSFER.name -> RidePaymentMethod.MANUAL_TRANSFER
                else -> null
            }
        }
        if (methods.isEmpty()) {
            throw ApiRequestException(409, "The server did not offer a payment method supported by this app.")
        }
        val economics = body.estimate.economics?.toDomainEconomics()
        if (economics != null && economics.passengerTotal != body.estimate.amount) {
            throw ApiRequestException(409, "The fare estimate does not reconcile with its economics snapshot.")
        }
        FareEstimate(
            amount = body.estimate.amount,
            currency = body.estimate.currency,
            pricingRuleVersion = body.estimate.pricingRuleVersion,
            paymentMethods = methods,
            economics = economics,
            serviceType = body.estimate.serviceType.toServiceType(),
            fixedRoute = body.estimate.fixedRoute?.toDomain(),
        )
    }

    override suspend fun publicCities(): List<PublicRideCity> = request {
        val response = client.get(api.endpoint("cities"))
        if (!response.status.isSuccess()) {
            throw ApiRequestException(response.status.value, "The server could not load service cities.")
        }
        response.body<PublicCityListResponse>().items.map(PublicCityResponse::toDomain)
    }

    override suspend fun fixedRoutes(cityId: String): FixedRouteCatalog? = request {
        val response = client.get(api.endpoint("cities/$cityId/fixed-routes"))
        if (response.status == HttpStatusCode.NotFound) return@request null
        if (!response.status.isSuccess()) {
            throw ApiRequestException(response.status.value, "The server could not load published fixed routes.")
        }
        response.body<PublicFixedRouteCatalogResponse>().toDomain()
    }

    override suspend fun estimateFixedRoute(directionVersionId: String): FareEstimate = request {
        val response = client.post(api.endpoint("rides/estimate")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(FixedRouteRideEstimateRequest(directionVersionId))
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) {
            throw ApiRequestException(response.status.value, "The server could not estimate this fixed route.")
        }
        response.body<RideEstimateResponse>().toDomain()
    }

    override suspend fun requestFixedRoute(
        directionVersionId: String,
        paymentMethod: RidePaymentMethod,
    ): RideSummary {
        val idempotencyKey = newIdempotencyKey()
        return idempotentRequest {
            val response = client.post(api.endpoint("rides")) {
                authorize()
                header("Idempotency-Key", idempotencyKey)
                contentType(ContentType.Application.Json)
                setBody(FixedRouteRideRequest(directionVersionId, paymentMethod.name))
            }
            response.rideOrThrow()
        }
    }

    override suspend fun currentRide(id: String): RideSummary = request {
        val response = client.get(api.endpoint("rides/$id")) { authorize() }
        response.rideOrThrow()
    }

    override suspend fun finalFare(id: String): FinalRideFare = request {
        val response = client.get(api.endpoint("rides/$id/fare")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load this receipt.")
        response.body<FareResponse>().toFinalFare()
    }

    override suspend fun receipt(id: String): RideReceipt = request {
        val response = client.get(api.endpoint("rides/$id/receipt")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load this receipt.")
        response.body<RideReceiptResponse>().toDomain()
    }

    override suspend fun listRides(): List<RideSummary> = request {
        val response = client.get(api.endpoint("rides")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load rides.")
        response.body<RideListResponse>().items.map { it.toSummary() }
    }

    override suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary {
        return requestRide(pickup, destination, RidePaymentMethod.CASH)
    }

    override suspend fun requestRide(
        pickup: Coordinates,
        destination: Coordinates,
        paymentMethod: RidePaymentMethod,
    ): RideSummary {
        val idempotencyKey = newIdempotencyKey()
        return idempotentRequest {
            val response = client.post(api.endpoint("rides")) {
                authorize()
                header("Idempotency-Key", idempotencyKey)
                contentType(ContentType.Application.Json)
                setBody(RideRequest(pickup.toRequest(), destination.toRequest(), paymentMethod.name))
            }
            response.rideOrThrow()
        }
    }

    override suspend fun submitManualTransfer(id: String, payerReference: String?): RideReceipt {
        val idempotencyKey = newIdempotencyKey()
        idempotentRequest {
            val response = client.post(api.endpoint("rides/$id/payments/manual-transfer/submit")) {
                authorize()
                header("Idempotency-Key", idempotencyKey)
                contentType(ContentType.Application.Json)
                setBody(ManualTransferClaimRequest(payerReference?.trim()?.ifEmpty { null }))
            }
            if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
            if (!response.status.isSuccess()) {
                throw ApiRequestException(response.status.value, "The server could not submit this transfer for review.")
            }
        }
        // The mutation response is only an acknowledgement. Reload the
        // authoritative receipt before rendering a payment state.
        return receipt(id)
    }

    override suspend fun cancelRide(id: String, reason: String): RideSummary {
        val idempotencyKey = newIdempotencyKey()
        return idempotentRequest {
            val response = client.post(api.endpoint("rides/$id/cancel")) {
                authorize()
                header("Idempotency-Key", idempotencyKey)
                contentType(ContentType.Application.Json)
                setBody(CancellationRequest(reason))
            }
            response.rideOrThrow()
        }
    }

    override suspend fun sendCoordinationMessage(
        id: String,
        code: RideCoordinationCode,
    ): RideCoordinationMessage {
        require(code != RideCoordinationCode.UNKNOWN)
        val idempotencyKey = newIdempotencyKey()
        return idempotentRequest {
            val response = client.post(api.endpoint("rides/$id/messages")) {
                authorize()
                header("Idempotency-Key", idempotencyKey)
                contentType(ContentType.Application.Json)
                setBody(RideCoordinationRequest(code.name))
            }
            if (response.status == HttpStatusCode.Unauthorized) {
                throw AuthenticationRejectedException()
            }
            if (!response.status.isSuccess()) {
                throw ApiRequestException(
                    response.status.value,
                    "The server could not send this ride update.",
                )
            }
            response.body<RideCoordinationResponse>().toDomain()
        }
    }

    override suspend fun ratings(id: String): List<RideRating> = request {
        val response = client.get(api.endpoint("rides/$id/ratings")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load ride feedback.")
        response.body<RideRatingListResponse>().items.map { RideRating(it.id, it.score, it.comment) }
    }

    override suspend fun submitRating(id: String, score: Int, comment: String?): RideRating = request {
        val response = client.post(api.endpoint("rides/$id/rating")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(RideRatingRequest(score, comment))
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not submit your feedback.")
        response.body<RideRatingResponse>().let { RideRating(it.id, it.score, it.comment) }
    }

    private suspend fun io.ktor.client.request.HttpRequestBuilder.authorize() {
        header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
    }

    private suspend fun io.ktor.client.statement.HttpResponse.rideOrThrow(): RideSummary {
        if (status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!status.isSuccess()) throw ApiRequestException(status.value, "The server could not complete this ride request.")
        val ride = body<RideResponse>()
        return ride.toSummary()
    }

    private suspend fun <T> request(block: suspend () -> T): T = try {
        block()
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (error: Exception) {
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
        } catch (retryError: AuthenticationRejectedException) {
            throw retryError
        } catch (retryError: ApiRequestException) {
            throw retryError
        } catch (_: Exception) {
            throw AuthenticationNetworkException()
        }
    }
}

@Serializable
private data class CoordinateRequest(val latitude: Double, val longitude: Double, val address: String? = null)

private fun Coordinates.toRequest() = CoordinateRequest(latitude, longitude, address?.trim()?.takeIf(String::isNotEmpty))

@Serializable
private data class RideRequest(
    val pickup: CoordinateRequest,
    val destination: CoordinateRequest,
    @SerialName("payment_method") val paymentMethod: String,
)

@Serializable
private data class RideEstimateRequest(val pickup: CoordinateRequest, val destination: CoordinateRequest)

@Serializable
private data class FixedRouteRideEstimateRequest(
    @SerialName("fixed_route_direction_version_id") val directionVersionId: String,
)

@Serializable
private data class FixedRouteRideRequest(
    @SerialName("fixed_route_direction_version_id") val directionVersionId: String,
    @SerialName("payment_method") val paymentMethod: String,
)

@Serializable
private data class CancellationRequest(val reason: String)

@Serializable
private data class RideRatingRequest(val score: Int, val comment: String? = null)

@Serializable
private data class ManualTransferClaimRequest(
    @SerialName("payer_reference") val payerReference: String? = null,
)

@Serializable
private data class RideResponse(
    val id: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    val pickup: CoordinateResponse,
    val destination: CoordinateResponse,
    val driver: AssignedDriverResponse? = null,
    @SerialName("last_known_driver_location")
    val lastKnownDriverLocation: LastKnownDriverLocationResponse? = null,
    @SerialName("payment_method") val paymentMethod: String = "CASH",
    @SerialName("service_type") val serviceType: String = "ON_DEMAND",
    @SerialName("fixed_route") val fixedRoute: FixedRouteRideSummaryResponse? = null,
    @SerialName("latest_coordination_message")
    val latestCoordinationMessage: RideCoordinationResponse? = null,
) {
    fun toSummary() = RideSummary(
        id = id,
        status = RideStatus.valueOf(status),
        completedAt = completedAt,
        driver = driver?.let {
            AssignedDriver(it.displayName, AssignedVehicle(it.vehicle.make, it.vehicle.model, it.vehicle.color, it.vehicle.taxiIdentifier))
        },
        lastKnownDriverLocation = lastKnownDriverLocation?.toDomain(),
        pickup = pickup.toDomain(),
        destination = destination.toDomain(),
        paymentMethod = paymentMethod.toPaymentMethod(),
        serviceType = serviceType.toServiceType(),
        fixedRoute = fixedRoute?.toDomain(),
        latestCoordinationMessage = latestCoordinationMessage?.toDomain(),
    )
}

@Serializable
private data class RideCoordinationRequest(val code: String)

@Serializable
internal data class RideCoordinationResponse(
    val id: String,
    @SerialName("ride_id") val rideId: String,
    @SerialName("sender_role") val senderRole: String,
    val code: String,
    @SerialName("created_at") val createdAt: String,
) {
    fun toDomain() = RideCoordinationMessage(
        id = id,
        rideId = rideId,
        senderRole = runCatching {
            RideCoordinationSenderRole.valueOf(senderRole)
        }.getOrDefault(RideCoordinationSenderRole.UNKNOWN),
        code = runCatching {
            RideCoordinationCode.valueOf(code)
        }.getOrDefault(RideCoordinationCode.UNKNOWN),
        createdAt = createdAt,
    )
}

@Serializable
internal data class RideListResponse(val items: List<RideListItemResponse>)

@Serializable
internal data class RideListItemResponse(
    val id: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    val driver: AssignedDriverResponse? = null,
    val pickup: CoordinateResponse,
    val destination: CoordinateResponse,
    @SerialName("payment_method") val paymentMethod: String = "CASH",
    @SerialName("service_type") val serviceType: String = "ON_DEMAND",
    @SerialName("fixed_route") val fixedRoute: FixedRouteRideSummaryResponse? = null,
) {
    fun toSummary() = RideSummary(
        id = id,
        status = RideStatus.valueOf(status),
        completedAt = completedAt,
        driver = driver?.let {
            AssignedDriver(it.displayName, AssignedVehicle(it.vehicle.make, it.vehicle.model, it.vehicle.color, it.vehicle.taxiIdentifier))
        },
        pickup = pickup.toDomain(),
        destination = destination.toDomain(),
        paymentMethod = paymentMethod.toPaymentMethod(),
        serviceType = serviceType.toServiceType(),
        fixedRoute = fixedRoute?.toDomain(),
    )
}

@Serializable
internal data class AssignedDriverResponse(
    @SerialName("display_name") val displayName: String,
    val vehicle: AssignedVehicleResponse,
)

@Serializable
internal data class AssignedVehicleResponse(
    val make: String,
    val model: String,
    val color: String,
    @SerialName("taxi_identifier") val taxiIdentifier: String? = null,
)

@Serializable
private data class LastKnownDriverLocationResponse(
    val latitude: Double,
    val longitude: Double,
    @SerialName("observed_at") val observedAt: String,
    @SerialName("accuracy_meters") val accuracyMeters: Double? = null,
) {
    fun toDomain() = LastKnownDriverLocation(
        coordinates = Coordinates(latitude, longitude),
        observedAt = observedAt,
        accuracyMeters = accuracyMeters,
    )
}

@Serializable
private data class RideEstimateResponse(
    val estimate: FareEstimateResponse,
    @SerialName("payment_methods") val paymentMethods: List<String> = listOf("CASH"),
)

@Serializable
private data class FareEstimateResponse(
    val amount: String,
    val currency: String,
    @SerialName("pricing_rule_version") val pricingRuleVersion: String,
    val economics: FareEconomicsResponse? = null,
    @SerialName("service_type") val serviceType: String = "ON_DEMAND",
    @SerialName("fixed_route") val fixedRoute: FixedRouteRideSummaryResponse? = null,
)

@Serializable
internal data class LocalizedTextResponse(
    val en: String,
    val fr: String,
    val ar: String,
) {
    fun toDomain() = LocalizedText(en, fr, ar)
}

@Serializable
internal data class FixedRouteRideSummaryResponse(
    @SerialName("direction_version_id") val directionVersionId: String,
    @SerialName("route_version_id") val routeVersionId: String,
    @SerialName("route_code") val routeCode: String,
    @SerialName("localized_route_name") val routeName: LocalizedTextResponse,
    @SerialName("direction_code") val directionCode: String,
    @SerialName("start_location_name") val startName: LocalizedTextResponse,
    @SerialName("finish_location_name") val finishName: LocalizedTextResponse,
) {
    fun toDomain() = FixedRouteRideSummary(
        directionVersionId,
        routeVersionId,
        routeCode,
        routeName.toDomain(),
        directionCode,
        startName.toDomain(),
        finishName.toDomain(),
    )
}

@Serializable
internal data class PublicCityListResponse(val items: List<PublicCityResponse>)

@Serializable
internal data class PublicCityResponse(
    val id: String,
    val code: String,
    @SerialName("localized_name") val name: LocalizedTextResponse,
    val timezone: String,
    @SerialName("lifecycle_status") val lifecycleStatus: String,
    @SerialName("booking_available") val bookingAvailable: Boolean,
) {
    fun toDomain() = PublicRideCity(
        id,
        code,
        name.toDomain(),
        timezone,
        lifecycleStatus,
        bookingAvailable,
    )
}

@Serializable
internal data class PublicFixedRouteCatalogResponse(
    val city: PublicCityResponse,
    val routes: List<PublicFixedRouteResponse>,
) {
    fun toDomain() = FixedRouteCatalog(
        city = city.toDomain(),
        directions = routes.flatMap { route ->
            route.versions.flatMap { version ->
                version.directions.map { it.toDomain(route.code, version) }
            }
        },
    )
}

@Serializable
internal data class PublicFixedRouteResponse(
    val code: String,
    val versions: List<PublicFixedRouteVersionResponse>,
)

@Serializable
internal data class PublicFixedRouteVersionResponse(
    val id: String,
    @SerialName("localized_name") val name: LocalizedTextResponse,
    val directions: List<PublicFixedRouteDirectionResponse>,
)

@Serializable
internal data class PublicFixedRouteDirectionResponse(
    val id: String,
    @SerialName("direction_code") val directionCode: String,
    @SerialName("start_location_name") val startName: LocalizedTextResponse,
    @SerialName("finish_location_name") val finishName: LocalizedTextResponse,
    val start: CoordinateResponse,
    val finish: CoordinateResponse,
    val geometry: PublicLineStringResponse,
    @SerialName("flat_fare") val flatFare: String,
    val currency: String,
    @SerialName("immediate_booking_enabled") val immediateBookingEnabled: Boolean,
    @SerialName("scheduled_booking_enabled") val scheduledBookingEnabled: Boolean,
    val stops: List<PublicFixedRouteStopResponse> = emptyList(),
) {
    fun toDomain(
        routeCode: String,
        version: PublicFixedRouteVersionResponse,
    ) = PublishedFixedRouteDirection(
        id = id,
        routeVersionId = version.id,
        routeCode = routeCode,
        routeName = version.name.toDomain(),
        directionCode = directionCode,
        startName = startName.toDomain(),
        finishName = finishName.toDomain(),
        start = start.toDomain(),
        finish = finish.toDomain(),
        geometry = geometry.coordinates.map { point ->
            if (point.size != 2 || point[0] !in -180.0..180.0 || point[1] !in -90.0..90.0) {
                throw ApiRequestException(409, "The published fixed-route geometry is invalid.")
            }
            Coordinates(latitude = point[1], longitude = point[0])
        }.also {
            if (it.size < 2) throw ApiRequestException(409, "The published fixed-route geometry is incomplete.")
        },
        flatFare = flatFare,
        currency = currency,
        immediateBookingEnabled = immediateBookingEnabled,
        scheduledBookingEnabled = scheduledBookingEnabled,
        stops = stops.map(PublicFixedRouteStopResponse::toDomain),
    )
}

@Serializable
internal data class PublicLineStringResponse(
    val type: String,
    val coordinates: List<List<Double>>,
)

@Serializable
internal data class PublicFixedRouteStopResponse(
    val sequence: Int,
    @SerialName("localized_name") val name: LocalizedTextResponse,
    val location: CoordinateResponse,
) {
    fun toDomain() = PublishedFixedRouteStop(sequence, name.toDomain(), location.toDomain())
}

private fun RideEstimateResponse.toDomain(): FareEstimate {
    val methods = paymentMethods.mapNotNull(String::toPaymentMethodOrNull)
    if (methods.isEmpty()) {
        throw ApiRequestException(409, "The server did not offer a payment method supported by this app.")
    }
    val domainEconomics = estimate.economics?.toDomainEconomics()
    if (domainEconomics != null && domainEconomics.passengerTotal != estimate.amount) {
        throw ApiRequestException(409, "The fare estimate does not reconcile with its economics snapshot.")
    }
    return FareEstimate(
        amount = estimate.amount,
        currency = estimate.currency,
        pricingRuleVersion = estimate.pricingRuleVersion,
        paymentMethods = methods,
        economics = domainEconomics,
        serviceType = estimate.serviceType.toServiceType(),
        fixedRoute = estimate.fixedRoute?.toDomain(),
    )
}

@Serializable
internal data class FareEconomicsResponse(
    @SerialName("transport_fare") val transportFare: String,
    @SerialName("scheduling_surcharge") val schedulingSurcharge: String,
    @SerialName("operator_service_fee") val operatorServiceFee: String,
    @SerialName("passenger_total") val passengerTotal: String,
    @SerialName("expected_driver_net") val expectedDriverNet: String,
    @SerialName("operator_allocation") val operatorAllocation: String,
    @SerialName("operator_fee_policy_version") val operatorFeePolicyVersion: String,
    @SerialName("operator_fee_calculation_mode") val operatorFeeCalculationMode: String,
    @SerialName("operator_fee_funding_mode") val operatorFeeFundingMode: String,
    @SerialName("scheduling_policy_version") val schedulingPolicyVersion: String? = null,
)

internal fun FareEconomicsResponse.toDomainEconomics() = FareEconomics(
    transportFare = transportFare,
    schedulingSurcharge = schedulingSurcharge,
    operatorServiceFee = operatorServiceFee,
    passengerTotal = passengerTotal,
    expectedDriverNet = expectedDriverNet,
    operatorAllocation = operatorAllocation,
    operatorFeePolicyVersion = operatorFeePolicyVersion,
    operatorFeeCalculationMode = operatorFeeCalculationMode,
    operatorFeeFundingMode = operatorFeeFundingMode,
    schedulingPolicyVersion = schedulingPolicyVersion,
)

@Serializable
internal data class FareResponse(
    val amount: String,
    val currency: String,
    @SerialName("pricing_rule_version") val pricingRuleVersion: String? = null,
    val components: List<FareComponentResponse> = emptyList(),
    val economics: FareEconomicsResponse? = null,
) {
    fun toFinalFare(): FinalRideFare {
        val domainEconomics = economics?.toDomainEconomics()
        if (domainEconomics != null && domainEconomics.passengerTotal != amount) {
            throw ApiRequestException(409, "The finalized fare does not reconcile with its economics snapshot.")
        }
        return FinalRideFare(
            amount = amount,
            currency = currency,
            pricingRuleVersion = pricingRuleVersion,
            components = components.map { FareComponent(it.code, it.label, it.amount) },
            economics = domainEconomics,
        )
    }
}

@Serializable
internal data class FareComponentResponse(val code: String, val label: String, val amount: String)

@Serializable
internal data class RideReceiptResponse(
    @SerialName("ride_id") val rideId: String,
    @SerialName("completed_at") val completedAt: String,
    val fare: FareResponse,
    val payment: PaymentReceiptResponse,
) {
    fun toDomain() = RideReceipt(
        rideId = rideId,
        completedAt = completedAt,
        fare = fare.toFinalFare(),
        paymentMethod = payment.method,
        paymentStatus = payment.status,
        manualTransfer = payment.manualTransfer?.toDomain(),
        refunds = payment.refunds?.toDomain(),
    )
}

@Serializable
internal data class PaymentReceiptResponse(
    val method: String,
    val status: String,
    @SerialName("manual_transfer") val manualTransfer: ManualTransferInstructionsResponse? = null,
    val refunds: PaymentRefundSummaryResponse? = null,
)

@Serializable
internal data class PaymentRefundSummaryResponse(
    @SerialName("refunded_amount") val refundedAmount: String,
    @SerialName("net_paid_amount") val netPaidAmount: String,
    val currency: String,
    val items: List<PaymentRefundResponse>,
) {
    fun toDomain() = org.example.taximobile.domain.rides.RideRefundSummary(
        refundedAmount = refundedAmount,
        netPaidAmount = netPaidAmount,
        currency = currency,
        items = items.map { it.toDomain() },
    )
}

@Serializable
internal data class PaymentRefundResponse(
    val id: String,
    val amount: String,
    val currency: String,
    val reason: String,
    @SerialName("refunded_at") val refundedAt: String,
) {
    fun toDomain() = org.example.taximobile.domain.rides.RideRefund(
        id = id,
        amount = amount,
        currency = currency,
        reason = reason,
        refundedAt = refundedAt,
    )
}

@Serializable
internal data class ManualTransferInstructionsResponse(
    @SerialName("recipient_name") val recipientName: String,
    @SerialName("bank_account") val bankAccount: String? = null,
    @SerialName("wallet_id") val walletId: String? = null,
    @SerialName("payment_reference") val paymentReference: String,
    @SerialName("latest_claim_status") val latestClaimStatus: String? = null,
) {
    fun toDomain() = ManualTransferInstructions(
        recipientName = recipientName,
        bankAccount = bankAccount,
        walletId = walletId,
        paymentReference = paymentReference,
        latestClaimStatus = latestClaimStatus,
    )
}

@Serializable
private data class RideRatingListResponse(val items: List<RideRatingResponse>)

@Serializable
private data class RideRatingResponse(
    val id: String,
    val score: Int,
    val comment: String? = null,
)

@Serializable
internal data class CoordinateResponse(
    val latitude: Double,
    val longitude: Double,
    val address: String? = null,
) {
    fun toDomain() = Coordinates(latitude, longitude, address?.trim()?.takeIf(String::isNotEmpty))
}

private fun String.toPaymentMethod(): RidePaymentMethod =
    runCatching { RidePaymentMethod.valueOf(this) }.getOrDefault(RidePaymentMethod.UNKNOWN)

private fun String.toPaymentMethodOrNull(): RidePaymentMethod? = when (this) {
    RidePaymentMethod.CASH.name -> RidePaymentMethod.CASH
    RidePaymentMethod.MANUAL_TRANSFER.name -> RidePaymentMethod.MANUAL_TRANSFER
    else -> null
}

private fun String.toServiceType(): RideServiceType =
    runCatching { RideServiceType.valueOf(this) }.getOrDefault(RideServiceType.UNKNOWN)
