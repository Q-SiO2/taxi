package org.example.taximobile.feature.app

import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertAll
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onAllNodesWithContentDescription
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import java.util.Locale
import org.example.taximobile.App
import org.example.taximobile.app.AppRole
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.auth.AccountRecoveryCodes
import org.example.taximobile.domain.auth.AccountSession
import org.example.taximobile.domain.drivers.DriverCredential
import org.example.taximobile.domain.drivers.DriverEarningItem
import org.example.taximobile.domain.drivers.DriverEarnings
import org.example.taximobile.domain.drivers.DriverRideOffer
import org.example.taximobile.domain.drivers.DriverRideSummary
import org.example.taximobile.domain.drivers.DriverVehicle
import org.example.taximobile.domain.rides.AssignedDriver
import org.example.taximobile.domain.rides.AssignedVehicle
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.FinalRideFare
import org.example.taximobile.domain.rides.FixedRouteCatalog
import org.example.taximobile.domain.rides.LastKnownDriverLocation
import org.example.taximobile.domain.rides.LocalizedText
import org.example.taximobile.domain.rides.ManualTransferInstructions
import org.example.taximobile.domain.rides.RideReceipt
import org.example.taximobile.domain.rides.RideRefund
import org.example.taximobile.domain.rides.RideRefundSummary
import org.example.taximobile.domain.rides.RideRating
import org.example.taximobile.domain.rides.RideSummary
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.PublicRideCity
import org.example.taximobile.domain.rides.PublishedFixedRouteDirection
import org.example.taximobile.domain.places.PlaceAttribution
import org.example.taximobile.domain.places.PlaceKind
import org.example.taximobile.domain.places.PlaceResult
import org.example.taximobile.domain.places.PlaceSearch
import org.example.taximobile.domain.safety.SafetyCategory
import org.example.taximobile.domain.safety.SafetyReport
import org.example.taximobile.domain.cooperatives.CooperativeMembership
import org.example.taximobile.feature.ui.text.UiMessage
import org.example.taximobile.feature.connectivity.ConnectivityStatus
import org.example.taximobile.feature.ui.text.ltrIsolate
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.message_account_created
import taximobile.shared.generated.resources.message_network_unavailable
import taximobile.shared.generated.resources.message_registration_failed

@OptIn(ExperimentalTestApi::class)
class CriticalStateUiTest {
    @Test
    fun passenger_can_choose_a_serviceable_backend_place_result() = runComposeUiTest {
        val city = PublicRideCity(
            id = "city-rabat",
            code = "rabat",
            name = LocalizedText("Rabat", "Rabat", "الرباط"),
            timezone = "Africa/Casablanca",
            lifecycleStatus = "PILOT",
            bookingAvailable = true,
        )
        setContent {
            App(
                state = AppUiState.PassengerReady(
                    serviceCities = listOf(city),
                    placeDiscovery = PlaceDiscoveryUiState(
                        revision = 1,
                        search = PlaceSearch(
                            cityId = city.id,
                            query = "Gare",
                            items = listOf(
                                PlaceResult(
                                    id = "result",
                                    primaryText = "Gare Rabat Ville",
                                    secondaryText = "Hassan, Rabat",
                                    coordinate = Coordinates(34.0209, -6.8416),
                                    kind = PlaceKind.POI,
                                    pickupServiceable = true,
                                ),
                            ),
                            attribution = PlaceAttribution(
                                "© OpenStreetMap contributors",
                                "https://www.openstreetmap.org/copyright",
                            ),
                        ),
                    ),
                ),
            )
        }

        onNodeWithText("Find a place").performScrollTo().performClick()
        onNodeWithText("Gare Rabat Ville").performScrollTo().assertIsDisplayed().performClick()
        onNodeWithTag("passenger-pickup-selection")
            .performScrollTo()
            .assertTextContains("Gare Rabat Ville, Hassan, Rabat")
        onNodeWithText("Review fare").assertIsNotEnabled()
    }

    @Test
    fun passenger_cannot_choose_an_outside_area_place_as_pickup() = runComposeUiTest {
        val city = PublicRideCity(
            id = "city-casablanca",
            code = "casablanca",
            name = LocalizedText("Casablanca", "Casablanca", "الدار البيضاء"),
            timezone = "Africa/Casablanca",
            lifecycleStatus = "PILOT",
            bookingAvailable = true,
        )
        setContent {
            App(
                state = AppUiState.PassengerReady(
                    serviceCities = listOf(city),
                    placeDiscovery = PlaceDiscoveryUiState(
                        revision = 1,
                        search = PlaceSearch(
                            cityId = city.id,
                            query = "Temara",
                            items = listOf(
                                PlaceResult(
                                    id = "outside",
                                    primaryText = "Temara",
                                    secondaryText = "Rabat-Sale-Kenitra",
                                    coordinate = Coordinates(33.9287, -6.9066),
                                    kind = PlaceKind.LOCALITY,
                                    pickupServiceable = false,
                                ),
                            ),
                            attribution = PlaceAttribution(
                                "© OpenStreetMap contributors",
                                "https://www.openstreetmap.org/copyright",
                            ),
                        ),
                    ),
                ),
            )
        }

        onNodeWithText("Find a place").performScrollTo().performClick()
        onNodeWithTag("place-result-outside").performScrollTo().assertIsNotEnabled()
        onNodeWithText("Outside this city’s pickup area").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun signed_out_passenger_starts_on_a_purpose_built_welcome_surface() = runComposeUiTest {
        setContent { App(state = AppUiState.SignedOut()) }

        onNodeWithText("Your city, one trusted taxi away").assertIsDisplayed()
        onNodeWithContentDescription("A taxi following a highlighted city route").assertIsDisplayed()
        onNodeWithText("Create account").assertIsDisplayed()
        onNodeWithText("Sign in").assertIsDisplayed()
    }

    @Test
    fun auth_switches_to_registration_and_exposes_validity_gated_submit() = runComposeUiTest {
        setContent { App(state = AppUiState.SignedOut()) }

        onNodeWithText("Create account", useUnmergedTree = true).performClick()
        onNodeWithText("Display name").assertIsDisplayed()
        onNodeWithTag("auth-submit").assertIsNotEnabled()
    }

    @Test
    fun recovery_form_requires_complete_inputs_and_submits_without_claiming_success() =
        runComposeUiTest {
            data class RecoverySubmission(
                val identifier: String,
                val code: String,
                val newPassword: String,
            )

            var submission: RecoverySubmission? = null
            setContent {
                App(
                    state = AppUiState.SignedOut(),
                    onRecoverAccount = { identifier, code, newPassword ->
                        submission = RecoverySubmission(identifier, code, newPassword)
                    },
                )
            }

            onNodeWithText("Sign in", useUnmergedTree = true).performClick()
            onNodeWithText("Use a recovery code").performClick()
            onNodeWithTag("account-recovery-submit").assertIsNotEnabled()
            onNodeWithText("Email or Moroccan phone number")
                .performTextInput("  passenger@example.test  ")
            onNodeWithText("Recovery code").performTextInput("23456-789AB-CDEFG-HJKLM")
            onNodeWithText("New password").performTextInput("replacement-password")
            onNodeWithTag("account-recovery-submit").assertIsEnabled().performClick()

            assertEquals(
                RecoverySubmission(
                    "passenger@example.test",
                    "23456-789AB-CDEFG-HJKLM",
                    "replacement-password",
                ),
                submission,
            )
        }

    @Test
    fun valid_registration_form_submits_trimmed_identity_without_inventing_phone() = runComposeUiTest {
        data class Submission(
            val displayName: String,
            val email: String?,
            val phoneNumber: String?,
            val password: String,
        )

        var submission: Submission? = null
        setContent {
            App(
                state = AppUiState.SignedOut(),
                onRegister = { displayName, email, phoneNumber, password ->
                    submission = Submission(displayName, email, phoneNumber, password)
                },
            )
        }

        onNodeWithText("Create account", useUnmergedTree = true).performClick()
        onNodeWithText("Display name").performTextInput("  Phone passenger  ")
        onNodeWithText("Email (optional)").performTextInput("  phone@example.test  ")
        onNodeWithText("Password").performTextInput("twelve-chars!")

        onNodeWithTag("auth-submit").assertIsEnabled().performClick()

        assertEquals(
            Submission(
                displayName = "Phone passenger",
                email = "phone@example.test",
                phoneNumber = null,
                password = "twelve-chars!",
            ),
            submission,
        )
    }

    @Test
    fun completed_registration_is_announced_as_success_not_as_an_error() = runComposeUiTest {
        setContent {
            App(
                state = AppUiState.SignedOut(
                    message = UiMessage(Res.string.message_account_created),
                    registrationCompleted = true,
                    suggestedIdentifier = "passenger@example.test",
                ),
            )
        }

        onNodeWithText("Account created. Sign in to continue.").assert(
            SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Polite),
        )
        onNodeWithText("passenger@example.test").assertIsDisplayed()
    }

    @Test
    fun registration_failure_remains_an_assertive_error_on_the_account_form() = runComposeUiTest {
        setContent {
            App(
                state = AppUiState.SignedOut(
                    message = UiMessage(Res.string.message_registration_failed),
                    showRegistrationForm = true,
                ),
            )
        }

        onNodeWithText("TaxiMobile could not create the account. Try again shortly.").assert(
            SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Assertive),
        )
        onNodeWithText("Display name").assertIsDisplayed()
    }

    @Test
    fun offline_retry_is_visible_and_dispatches_only_the_retry_intent() = runComposeUiTest {
        var retried = false
        setContent {
            App(
                state = AppUiState.Offline(UiMessage(Res.string.message_network_unavailable)),
                onRetry = { retried = true },
            )
        }

        onNodeWithText("Connection unavailable").assertIsDisplayed()
        onNodeWithText("Network unavailable. Try again when connected.").assertIsDisplayed()
        onNodeWithText("Retry connection").performClick()
        assertTrue(retried)
    }

    @Test
    fun connectivity_drop_keeps_loaded_passenger_content_under_a_sticky_warning() = runComposeUiTest {
        setContent {
            App(
                state = AppUiState.PassengerReady(),
                connectivityStatus = ConnectivityStatus.UNAVAILABLE,
                showManualCoordinateEntry = false,
            )
        }

        onNodeWithText("Network unavailable. Try again when connected.").assertIsDisplayed()
        onNodeWithText("Choose the pickup on the map.").assertIsDisplayed()
        onAllNodesWithText("Connection unavailable").assertCountEquals(0)
    }

    @Test
    fun assigned_passenger_state_renders_backend_driver_and_status() = runComposeUiTest {
        val observedAt = "2026-08-13T12:00:00Z"
        var refreshRequested = false
        setContent {
            App(
                state = AppUiState.PassengerReady(
                    activeRideId = "ride-1",
                    activeRide = RideStatus.ACCEPTED,
                    assignedDriver = AssignedDriver(
                        displayName = "Samira",
                        vehicle = AssignedVehicle("Dacia", "Logan", "White", "TX-1234"),
                    ),
                    lastKnownDriverLocation = LastKnownDriverLocation(
                        coordinates = Coordinates(33.5731, -7.5898),
                        observedAt = observedAt,
                        accuracyMeters = 8.0,
                    ),
                ),
                onRefresh = { refreshRequested = true },
            )
        }

        onAllNodesWithText("Driver is on the way")[0].assertIsDisplayed()
        onNodeWithContentDescription("Recenter trip route").assertIsDisplayed()
        onAllNodesWithContentDescription("Driver is on the way status").assertAll(
            SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Polite),
        )
        onNodeWithText("Samira").assertIsDisplayed()
        onNodeWithText(ltrIsolate("TX-1234")).assertIsDisplayed()
        onNodeWithText("Last known driver position · observed ${ltrIsolate(observedAt)}").assertIsDisplayed()
        onNodeWithContentDescription("Refresh ride status and driver position").performClick()
        assertTrue(refreshRequested)
        onNodeWithText("Cancel request").assertIsEnabled()
    }

    @Test
    fun passenger_secondary_panels_keep_the_backend_active_ride_status_visible() = runComposeUiTest {
        setContent {
            App(
                state = AppUiState.PassengerReady(
                    activeRideId = "ride-active",
                    activeRide = RideStatus.IN_PROGRESS,
                ),
            )
        }

        onNodeWithText("Inbox").performClick()
        onNodeWithText("Ride in progress").assertIsDisplayed()
        onNodeWithText("Back to ride").performClick()

        onNodeWithText("Account").performClick()
        onNodeWithText("Ride in progress").assertIsDisplayed()
    }

    @Test
    fun passenger_safety_report_is_separate_from_support_and_ride_bound() = runComposeUiTest {
        var submission: Triple<String, SafetyCategory, String>? = null
        setContent {
            App(
                state = AppUiState.PassengerReady(
                    activeRideId = "ride-active-1234",
                    activeRide = RideStatus.IN_PROGRESS,
                    safetyReports = listOf(
                        SafetyReport(
                            id = "report-1",
                            rideId = "ride-active-1234",
                            category = SafetyCategory.UNSAFE_DRIVING,
                            status = "ACKNOWLEDGED",
                            createdAt = "2026-08-24T12:00:00Z",
                            latestPublicMessage = "A safety specialist is reviewing your report.",
                        )
                    ),
                ),
                onCreateSafetyReport = { rideId, category, description ->
                    submission = Triple(rideId, category, description)
                },
            )
        }

        onNodeWithText("Safety").performClick()
        onNodeWithText(
            "TaxiMobile safety reports are not an emergency service. If you are in immediate danger, move to a safe place and contact local emergency services."
        ).performScrollTo().assertIsDisplayed()
        onNodeWithText("Latest response: A safety specialist is reviewing your report.")
            .performScrollTo().assertIsDisplayed()
        onNodeWithText("Describe the safety concern").performScrollTo()
            .performTextInput("Vehicle door would not close")
        onNodeWithText("Send safety report").performScrollTo().assertIsEnabled().performClick()

        assertEquals(
            Triple("ride-active-1234", SafetyCategory.OTHER_SAFETY, "Vehicle door would not close"),
            submission,
        )
    }

    @Test
    fun driver_secondary_panels_keep_the_backend_active_ride_status_visible() = runComposeUiTest {
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.ON_RIDE,
                    activeRideId = "ride-active",
                    activeRide = RideStatus.IN_PROGRESS,
                ),
            )
        }

        onNodeWithText("Inbox").performClick()
        onNodeWithText("Ride in progress").assertIsDisplayed()
        onNodeWithText("Back to operations").performClick()

        onNodeWithText("Driver account").performClick()
        onNodeWithText("Ride in progress").assertIsDisplayed()
    }

    @Test
    fun driver_safety_shortcut_submits_only_a_bound_controlled_report() = runComposeUiTest {
        var submission: Triple<String, SafetyCategory, String>? = null
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.ON_RIDE,
                    activeRideId = "driver-ride-1234",
                    activeRide = RideStatus.IN_PROGRESS,
                ),
                onCreateSafetyReport = { rideId, category, description ->
                    submission = Triple(rideId, category, description)
                },
            )
        }

        onNodeWithText("Safety").performClick()
        onNodeWithText("Describe the safety concern").performTextInput("Passenger made a threat")
        onNodeWithText("Send safety report").assertIsEnabled().performClick()

        assertEquals(
            Triple("driver-ride-1234", SafetyCategory.OTHER_SAFETY, "Passenger made a threat"),
            submission,
        )
    }

    @Test
    fun offline_driver_cannot_go_online_without_readiness_evidence() = runComposeUiTest {
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(availability = DriverAvailabilityStatus.OFFLINE),
            )
        }

        onNodeWithText("Offline", useUnmergedTree = true).assertIsDisplayed()
        onNodeWithText("Select a verified vehicle", useUnmergedTree = true).assertIsDisplayed()
        onNodeWithText("Location required", useUnmergedTree = true).assertIsDisplayed()
        onNodeWithContentDescription("Recenter map").assertIsDisplayed()
        onNodeWithTag("driver-go-online").assertIsNotEnabled()
    }

    @Test
    fun pending_driver_availability_action_disables_button_and_exposes_loading_state() = runComposeUiTest {
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.OFFLINE,
                    activeVehicleId = "vehicle-1",
                    currentLocation = Coordinates(33.5731, -7.5898),
                    vehicles = listOf(
                        DriverVehicle(
                            id = "vehicle-1",
                            make = "Dacia",
                            model = "Logan",
                            color = "White",
                            status = "ACTIVE",
                            verificationStatus = "VERIFIED",
                        ),
                    ),
                ),
                pendingAction = AppAction(AppActionKind.SET_DRIVER_AVAILABILITY),
            )
        }

        onNodeWithTag("driver-go-online")
            .assertIsNotEnabled()
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Loading"))
    }

    @Test
    fun production_passenger_place_selection_hides_manual_coordinate_fields() = runComposeUiTest {
        setContent {
            App(
                state = AppUiState.PassengerReady(),
                showManualCoordinateEntry = false,
            )
        }

        onNodeWithText("Choose the pickup on the map.").assertIsDisplayed()
        onAllNodesWithText("Choose the destination on the map.").assertCountEquals(1)
        onAllNodesWithText("Pickup latitude").assertCountEquals(0)
        onAllNodesWithText("Destination longitude").assertCountEquals(0)
    }

    @Test
    fun passenger_fixed_route_catalog_shows_static_direction_and_requests_backend_quote() = runComposeUiTest {
        var estimatedDirection: String? = null
        val city = PublicRideCity(
            id = "city-1",
            code = "RABAT",
            name = LocalizedText("Rabat", "Rabat", "الرباط"),
            timezone = "Africa/Casablanca",
            lifecycleStatus = "ACTIVE",
            bookingAvailable = true,
        )
        val direction = PublishedFixedRouteDirection(
            id = "direction-1",
            routeVersionId = "version-1",
            routeCode = "RABAT_01",
            routeName = LocalizedText("Station route", "Ligne de la gare", "خط المحطة"),
            directionCode = "OUTBOUND",
            startName = LocalizedText("Station", "Gare", "المحطة"),
            finishName = LocalizedText("University", "Université", "الجامعة"),
            start = Coordinates(34.02, -6.84),
            finish = Coordinates(34.00, -6.80),
            geometry = listOf(Coordinates(34.02, -6.84), Coordinates(34.00, -6.80)),
            flatFare = "8.00",
            currency = "MAD",
            immediateBookingEnabled = true,
            scheduledBookingEnabled = false,
            stops = emptyList(),
        )
        setContent {
            App(
                state = AppUiState.PassengerReady(
                    serviceCities = listOf(city),
                    fixedRouteCatalog = FixedRouteCatalog(city, listOf(direction)),
                ),
                showManualCoordinateEntry = false,
                onEstimateFixedRoute = { estimatedDirection = it },
            )
        }

        onNodeWithText("Browse fixed routes").performClick()
        onNodeWithText("Station → University").assertIsDisplayed().performClick()
        onNodeWithText("8.00 MAD · OUTBOUND").assertIsDisplayed()
        onNodeWithText("Review flat fare").assertIsEnabled().performClick()
        assertEquals("direction-1", estimatedDirection)
    }

    @Test
    fun passenger_location_fab_admits_only_one_pending_platform_request() = runComposeUiTest {
        var requestCount = 0
        setContent {
            App(
                state = AppUiState.PassengerReady(),
                onRequestCurrentLocation = {
                    requestCount += 1
                    // Keep the first platform request pending for this assertion.
                },
            )
        }

        val locationFab = onNodeWithContentDescription("Use current location for pickup")
        locationFab.performClick()
        locationFab.performClick()

        assertEquals(1, requestCount)
        locationFab
            .assertIsNotEnabled()
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Loading"))
    }

    @Test
    fun passenger_can_select_a_recent_completed_destination() = runComposeUiTest {
        setContent {
            App(
                state = AppUiState.PassengerReady(
                    rideHistory = listOf(
                        org.example.taximobile.domain.rides.RideSummary(
                            id = "ride-completed",
                            status = RideStatus.COMPLETED,
                            destination = Coordinates(33.5890, -7.5910, "Casa Voyageurs"),
                        ),
                    ),
                ),
            )
        }

        onNodeWithText("Recent destinations").performScrollTo().assertIsDisplayed()
        onNodeWithText("Casa Voyageurs").performScrollTo().performClick()
        // The destination field now presents the useful backend address instead
        // of replacing it with the generic selected-state copy.
        onAllNodesWithText("Casa Voyageurs").assertCountEquals(2)
        onNodeWithText("Review fare").assertIsNotEnabled()
    }

    @Test
    fun passenger_history_row_loads_and_renders_authorized_receipt_detail() = runComposeUiTest {
        val ride = org.example.taximobile.domain.rides.RideSummary(
            id = "ride-history",
            status = RideStatus.COMPLETED,
            completedAt = "2026-08-13T12:00:00Z",
            pickup = Coordinates(33.5731, -7.5898, "Pickup"),
            destination = Coordinates(33.5890, -7.5910, "Casa Voyageurs"),
        )
        val renderedState = mutableStateOf(AppUiState.PassengerReady(rideHistory = listOf(ride)))
        var selectedRideId: String? = null
        setContent {
            App(
                state = renderedState.value,
                onSelectPassengerRide = { rideId ->
                    selectedRideId = rideId
                    renderedState.value = renderedState.value.copy(
                        selectedHistoryRide = ride,
                        selectedHistoryReceipt = RideReceipt(
                            rideId = rideId,
                            completedAt = ride.completedAt!!,
                            fare = FinalRideFare("42.00", "MAD", "casablanca-v1"),
                            paymentMethod = "CASH",
                            paymentStatus = "COMPLETED",
                            refunds = RideRefundSummary(
                                refundedAmount = "5.00",
                                netPaidAmount = "37.00",
                                currency = "MAD",
                                items = listOf(
                                    RideRefund(
                                        id = "refund-1",
                                        amount = "5.00",
                                        currency = "MAD",
                                        reason = "FARE_CORRECTION",
                                        refundedAt = "2026-08-13T13:00:00Z",
                                    ),
                                ),
                            ),
                        ),
                    )
                },
            )
        }

        onNodeWithText("Account").performClick()
        onNodeWithText("Ride completed · ${ltrIsolate("ride-his")}").performScrollTo().performClick()
        assertTrue(selectedRideId == "ride-history")
        onNodeWithText("Ride details").performScrollTo().assertIsDisplayed()
        onNodeWithText("Destination: Casa Voyageurs").performScrollTo().assertIsDisplayed()
        onNodeWithText("Receipt").performScrollTo().assertIsDisplayed()
        onNodeWithText("42.00").performScrollTo().assertIsDisplayed()
        onNodeWithText("Refunded: 5.00 MAD").performScrollTo().assertIsDisplayed()
        onNodeWithText("Net paid after refunds: 37.00 MAD").performScrollTo().assertIsDisplayed()
        onNodeWithText("Fare correction · −5.00 MAD").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun pending_cash_receipt_is_not_presented_as_paid() = runComposeUiTest {
        setContent {
            App(
                state = AppUiState.PassengerReady(
                    latestCompletedReceipt = RideReceipt(
                        rideId = "ride-cash",
                        completedAt = "2026-08-13T12:00:00Z",
                        fare = FinalRideFare("42.00", "MAD", "casablanca-v1"),
                        paymentMethod = "CASH",
                        paymentStatus = "PENDING",
                    ),
                ),
            )
        }

        onNodeWithText("Account").performClick()
        onNodeWithText("Cash settlement is awaiting the driver’s backend confirmation.").assertIsDisplayed()
        onAllNodesWithText("Paid").assertCountEquals(0)
    }

    @Test
    fun manual_transfer_receipt_requires_operator_review_before_success() = runComposeUiTest {
        var submittedRideId: String? = null
        var submittedReference: String? = null
        setContent {
            App(
                state = AppUiState.PassengerReady(
                    latestCompletedReceipt = RideReceipt(
                        rideId = "ride-transfer",
                        completedAt = "2026-08-23T12:00:00Z",
                        fare = FinalRideFare("42.00", "MAD", "casablanca-v1"),
                        paymentMethod = "MANUAL_TRANSFER",
                        paymentStatus = "PENDING",
                        manualTransfer = ManualTransferInstructions(
                            recipientName = "TaxiMobile Pilot",
                            bankAccount = "ACCOUNT-123",
                            walletId = null,
                            paymentReference = "TM-REFERENCE-123",
                            latestClaimStatus = "REJECTED",
                        ),
                    ),
                ),
                onSubmitManualTransfer = { rideId, reference ->
                    submittedRideId = rideId
                    submittedReference = reference
                },
            )
        }

        onNodeWithText("Account").performClick()
        onNodeWithText("Required payment reference: ${ltrIsolate("TM-REFERENCE-123")}")
            .performScrollTo()
            .assertIsDisplayed()
        onNodeWithText(
            "The previous transfer could not be matched. Check the reference or contact support, then submit again."
        ).assertIsDisplayed()
        onNodeWithText("Bank transaction reference (optional)").performTextInput("A")
        onNodeWithText("Use at least 3 characters, or leave this field empty.").assertIsDisplayed()
        onNodeWithText("I sent the transfer").assertIsNotEnabled()
        onNodeWithText("Bank transaction reference (optional)").performTextInput("BC")
        onNodeWithText("I sent the transfer").performScrollTo().assertIsEnabled().performClick()
        assertEquals("ride-transfer", submittedRideId)
        assertEquals("ABC", submittedReference)
        onAllNodesWithText("Paid").assertCountEquals(0)
    }

    @Test
    fun fully_refunded_transfer_is_not_presented_as_unverified_or_retryable() = runComposeUiTest {
        setContent {
            App(
                state = AppUiState.PassengerReady(
                    latestCompletedReceipt = RideReceipt(
                        rideId = "ride-refunded-transfer",
                        completedAt = "2026-08-24T12:00:00Z",
                        fare = FinalRideFare("42.00", "MAD", "casablanca-v1"),
                        paymentMethod = "MANUAL_TRANSFER",
                        paymentStatus = "REFUNDED",
                        manualTransfer = ManualTransferInstructions(
                            recipientName = "TaxiMobile Pilot",
                            bankAccount = "ACCOUNT-123",
                            walletId = null,
                            paymentReference = "TM-REFUNDED-123",
                            latestClaimStatus = "VERIFIED",
                        ),
                        refunds = RideRefundSummary(
                            refundedAmount = "42.00",
                            netPaidAmount = "0.00",
                            currency = "MAD",
                            items = listOf(
                                RideRefund(
                                    id = "refund-full",
                                    amount = "42.00",
                                    currency = "MAD",
                                    reason = "SERVICE_RECOVERY",
                                    refundedAt = "2026-08-24T13:00:00Z",
                                ),
                            ),
                        ),
                    ),
                ),
            )
        }

        onNodeWithText("Account").performClick()
        onNodeWithText("Transfer verified by the operator.").performScrollTo().assertIsDisplayed()
        onNodeWithText("Net paid after refunds: 0.00 MAD").performScrollTo().assertIsDisplayed()
        onAllNodesWithText("This transfer needs attention. Review the status or contact support.")
            .assertCountEquals(0)
        onAllNodesWithText("I sent the transfer").assertCountEquals(0)
    }

    @Test
    fun driver_cash_settlement_requires_explicit_confirmation() = runComposeUiTest {
        var settledRideId: String? = null
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.AVAILABLE,
                    pendingCashRideId = "ride-cash",
                ),
                onSettleDriverCash = { settledRideId = it },
            )
        }

        onNodeWithText("Confirm cash received").performClick()
        assertTrue(settledRideId == null)
        onNodeWithText("Cash received").performClick()
        assertTrue(settledRideId == "ride-cash")
    }

    @Test
    fun backend_confirmed_cash_settlement_renders_success_row() = runComposeUiTest {
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(availability = DriverAvailabilityStatus.AVAILABLE),
                completedAction = AppActionCompletion(
                    sequence = 1,
                    action = AppAction(AppActionKind.SETTLE_DRIVER_CASH, "ride-cash"),
                ),
            )
        }

        onNodeWithText("Cash receipt confirmed").assertIsDisplayed()
    }

    @Test
    fun backend_confirmed_rating_renders_success_row_in_passenger_account() = runComposeUiTest {
        setContent {
            App(
                state = AppUiState.PassengerReady(),
                completedAction = AppActionCompletion(
                    sequence = 1,
                    action = AppAction(AppActionKind.SUBMIT_RATING, "ride-rated"),
                ),
            )
        }

        onNodeWithText("Account").performClick()
        onNodeWithText("Rating submitted").assertIsDisplayed()
    }

    @Test
    fun passenger_rating_uses_accessible_stars_and_submits_the_selected_score() = runComposeUiTest {
        var submittedScore: Int? = null
        setContent {
            App(
                state = AppUiState.PassengerReady(rateableRideId = "ride-rateable"),
                onSubmitRating = { _, score, _ -> submittedScore = score },
            )
        }

        onNodeWithText("Account").performClick()
        onNodeWithContentDescription("3 star rating").performScrollTo().performClick()
        onNodeWithText("Submit rating").performScrollTo().performClick()
        assertEquals(3, submittedScore)
    }

    @Test
    fun empty_passenger_history_has_an_explanatory_state() = runComposeUiTest {
        setContent { App(state = AppUiState.PassengerReady()) }

        onNodeWithText("Account").performClick()
        onNodeWithText("No trips yet").performScrollTo().assertIsDisplayed()
        onNodeWithText("Completed and cancelled rides will appear here after your first request.")
            .performScrollTo().assertIsDisplayed()
    }

    @Test
    fun passenger_account_displays_sessions_and_one_time_recovery_codes() = runComposeUiTest {
        var state by mutableStateOf<AppUiState>(
            AppUiState.PassengerReady(
                accountSecurity = AccountSecurityUiState(
                    loaded = true,
                    sessions = listOf(
                        AccountSession(
                            id = "session-1",
                            deviceLabel = "Android passenger app",
                            current = true,
                            createdAt = "2026-09-02T10:00:00Z",
                            expiresAt = "2026-10-02T10:00:00Z",
                        ),
                    ),
                    recoveryCodes = AccountRecoveryCodes(
                        listOf("23456-789AB-CDEFG-HJKLM"),
                        "2027-03-01T10:00:00Z",
                    ),
                ),
            ),
        )
        setContent {
            App(
                state = state,
                onAcknowledgeRecoveryCodes = {
                    state = state.clearVisibleRecoveryCodes()
                },
            )
        }

        onNodeWithText("Account").performClick()
        onNodeWithText("Account security").performScrollTo().assertIsDisplayed()
        onNodeWithText("Android passenger app").performScrollTo().assertIsDisplayed()
        onNodeWithText(ltrIsolate("23456-789AB-CDEFG-HJKLM"))
            .performScrollTo().assertIsDisplayed()
        onNodeWithTag("clear-recovery-codes").performScrollTo().assertIsNotEnabled()
        onNodeWithTag("recovery-codes-saved-check").performClick()
        onNodeWithTag("clear-recovery-codes").assertIsEnabled().performClick()
        onAllNodesWithText(ltrIsolate("23456-789AB-CDEFG-HJKLM")).assertCountEquals(0)
    }

    @Test
    fun driver_account_displays_private_cooperative_membership() = runComposeUiTest {
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.OFFLINE,
                    cooperativeMembership = CooperativeMembership(
                        cooperativeId = "cooperative",
                        cooperativeName = "Casablanca Taxi Cooperative",
                        status = "ACTIVE",
                        joinedAt = "2026-01-01T00:00:00Z",
                        membershipNumber = "MEMBER-123",
                    ),
                ),
            )
        }

        onNodeWithText("Driver account").performClick()
        onNodeWithText("Cooperative membership").performScrollTo().assertIsDisplayed()
        onNodeWithText("Casablanca Taxi Cooperative").performScrollTo().assertIsDisplayed()
        onNodeWithText("Status: ACTIVE").performScrollTo().assertIsDisplayed()
        onNodeWithText("Member number: ${ltrIsolate("MEMBER-123")}").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun driver_account_displays_privacy_minimized_professional_credentials() = runComposeUiTest {
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.OFFLINE,
                    displayName = "Integration Driver",
                    verificationStatus = "APPROVED",
                    accountStatus = "ACTIVE",
                    credentials = listOf(
                        DriverCredential(
                            id = "credential",
                            type = "DRIVER_LICENSE",
                            status = "VERIFIED",
                            issuedAt = "2025-08-13T00:00:00Z",
                            expiresAt = "2027-08-13T00:00:00Z",
                        )
                    ),
                ),
            )
        }

        onAllNodesWithText("Integration Driver")[0].performClick()
        onAllNodesWithText("Integration Driver")[1].performScrollTo().assertIsDisplayed()
        onNodeWithText("Verification: Verified").performScrollTo().assertIsDisplayed()
        onNodeWithText("Account status: Active").performScrollTo().assertIsDisplayed()
        onNodeWithText("Professional credentials").performScrollTo().assertIsDisplayed()
        onNodeWithText("${ltrIsolate("DRIVER_LICENSE")} · ${ltrIsolate("VERIFIED")}")
            .performScrollTo().assertIsDisplayed()
        onNodeWithText("Expires: ${ltrIsolate("2027-08-13T00:00:00Z")}")
            .performScrollTo().assertIsDisplayed()
    }

    @Test
    fun driver_account_displays_backend_settlement_summary_and_rows() = runComposeUiTest {
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.OFFLINE,
                    earnings = DriverEarnings(
                        currency = "MAD",
                        gross = "35.00",
                        fees = "0.00",
                        adjustments = "0.00",
                        net = "35.00",
                        settledThrough = "2026-08-13T12:00:00Z",
                        count = 1,
                        items = listOf(
                            DriverEarningItem(
                                id = "earning",
                                rideId = "ride-12345678",
                                gross = "35.00",
                                fees = "0.00",
                                adjustments = "0.00",
                                net = "35.00",
                                currency = "MAD",
                                settledAt = "2026-08-13T12:00:00Z",
                            )
                        ),
                    ),
                ),
            )
        }

        onNodeWithText("Driver account").performClick()
        onNodeWithText("Settled rides: 1").performScrollTo().assertIsDisplayed()
        onNodeWithText("Settled through: ${ltrIsolate("2026-08-13T12:00:00Z")}")
            .performScrollTo().assertIsDisplayed()
        onNodeWithText(
            "Ride ${ltrIsolate("ride-123")} · 35.00 MAD · ${ltrIsolate("2026-08-13T12:00:00Z")}",
        ).performScrollTo().assertIsDisplayed()
    }

    @Test
    fun driver_history_row_loads_and_renders_authorized_passenger_feedback() = runComposeUiTest {
        val detail = RideSummary(
            id = "ride-history",
            status = RideStatus.COMPLETED,
            completedAt = "2026-08-13T12:00:00Z",
            pickup = Coordinates(33.5731, -7.5898, "Pickup"),
            destination = Coordinates(33.5890, -7.5910, "Casa Voyageurs"),
        )
        val renderedState = mutableStateOf(
            AppUiState.DriverReady(
                availability = DriverAvailabilityStatus.OFFLINE,
                rideHistory = listOf(DriverRideSummary(detail.id, detail.status, detail.completedAt)),
            )
        )
        var selectedRideId: String? = null
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = renderedState.value,
                onSelectDriverRide = { rideId ->
                    selectedRideId = rideId
                    renderedState.value = renderedState.value.copy(
                        selectedHistoryRide = detail,
                        selectedHistoryRating = RideRating("rating", 5, "Smooth ride"),
                    )
                },
            )
        }

        onNodeWithText("Driver account").performClick()
        onNodeWithTag("driver-history-ride-history").performScrollTo().performClick()
        assertTrue(selectedRideId == "ride-history")
        onNodeWithText("Ride details").performScrollTo().assertIsDisplayed()
        onNodeWithText("Destination: Casa Voyageurs").performScrollTo().assertIsDisplayed()
        onNodeWithText("Passenger feedback").performScrollTo().assertIsDisplayed()
        onNodeWithText("Passenger rating: 5/5").performScrollTo().assertIsDisplayed()
        onNodeWithText("Comment: Smooth ride").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun expired_driver_offer_disables_accept_and_requests_refresh() = runComposeUiTest {
        var refreshRequested = false
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.AVAILABLE,
                    offers = listOf(
                        DriverRideOffer(
                            id = "offer-expired",
                            rideId = "ride-1",
                            pickup = Coordinates(33.5731, -7.5898),
                            issuedAt = "2026-08-13T11:59:00Z",
                            expiresAt = "2026-08-13T12:00:00Z",
                            serverTimeAtFetch = "2026-08-13T12:00:01Z",
                        ),
                    ),
                ),
                onRefresh = { refreshRequested = true },
            )
        }

        onNodeWithText("Offer expired · refreshing").assertIsDisplayed()
        onNodeWithText("Accept").assertIsNotEnabled()
        assertTrue(refreshRequested)
    }

    @Test
    fun malformed_driver_offer_timing_disables_accept_and_requests_refresh() = runComposeUiTest {
        var refreshRequested = false
        setContent {
            App(
                appRole = AppRole.DRIVER,
                state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.AVAILABLE,
                    offers = listOf(
                        DriverRideOffer(
                            id = "offer-malformed",
                            rideId = "ride-1",
                            pickup = Coordinates(33.5731, -7.5898),
                            issuedAt = "not-an-instant",
                            expiresAt = "2026-08-13T12:00:00Z",
                            serverTimeAtFetch = "2026-08-13T11:59:30Z",
                        ),
                    ),
                ),
                onRefresh = { refreshRequested = true },
            )
        }

        onNodeWithText("Offer timing unavailable · refreshing").assertIsDisplayed()
        onNodeWithText("Accept").assertIsNotEnabled()
        assertTrue(refreshRequested)
    }

    @Test
    fun french_catalog_is_selected_from_the_platform_locale() {
        withLocale("fr") {
            runComposeUiTest {
                setContent { App(state = AppUiState.SignedOut()) }

                onAllNodesWithText("Créer un compte", useUnmergedTree = true)[0].assertIsDisplayed()
                onAllNodesWithText("Se connecter", useUnmergedTree = true)[0].assertIsDisplayed()
            }
        }
    }

    @Test
    fun arabic_catalog_uses_right_to_left_control_order() {
        withLocale("ar") {
            runComposeUiTest {
                setContent { App(state = AppUiState.SignedOut()) }

                onNodeWithText("تسجيل الدخول", useUnmergedTree = true).performClick()
                val signIn = onAllNodesWithText("تسجيل الدخول", useUnmergedTree = true)[0]
                    .fetchSemanticsNode().boundsInRoot
                val createAccount = onAllNodesWithText("إنشاء حساب", useUnmergedTree = true)[0]
                    .fetchSemanticsNode().boundsInRoot
                assertTrue(signIn.left > createAccount.left)
            }
        }
    }
}

private fun withLocale(language: String, block: () -> Unit) {
    val original = Locale.getDefault()
    try {
        Locale.setDefault(Locale.forLanguageTag(language))
        block()
    } finally {
        Locale.setDefault(original)
    }
}
