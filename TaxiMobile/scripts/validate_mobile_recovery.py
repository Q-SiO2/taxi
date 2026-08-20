"""Portable source gate for authoritative mobile connectivity/lifecycle recovery."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MobileRecoveryConfigurationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MobileRecoveryConfigurationError(message)


def validate_mobile_recovery(root: Path = ROOT) -> None:
    common = (root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/connectivity/Connectivity.kt").read_text(
        encoding="utf-8",
    )
    android_root = (root / "androidApp/src/main/kotlin/org/example/taximobile/MainActivity.kt").read_text(
        encoding="utf-8",
    )
    android_observer = (root / "androidApp/src/main/kotlin/org/example/taximobile/AndroidConnectivityObserver.kt").read_text(
        encoding="utf-8",
    )
    manifest = (root / "androidApp/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    ios_root = (root / "shared/src/iosMain/kotlin/org/example/taximobile/MainViewController.kt").read_text(
        encoding="utf-8",
    )
    ios_observer = (root / "shared/src/iosMain/kotlin/org/example/taximobile/IosConnectivityObserver.kt").read_text(
        encoding="utf-8",
    )
    action_model = (root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/app/AppAction.kt").read_text(
        encoding="utf-8",
    )
    app = (root / "shared/src/commonMain/kotlin/org/example/taximobile/App.kt").read_text(encoding="utf-8")
    passenger = (root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt").read_text(
        encoding="utf-8",
    )
    driver = (root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt").read_text(
        encoding="utf-8",
    )
    screen = (root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt").read_text(
        encoding="utf-8",
    )
    shared_sections = (root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt").read_text(
        encoding="utf-8",
    )
    location_gate = (root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/location/OneShotLocationGate.kt").read_text(
        encoding="utf-8",
    )
    android_location = (root / "androidApp/src/main/kotlin/org/example/taximobile/AndroidCurrentLocationRequester.kt").read_text(
        encoding="utf-8",
    )
    ios_location = (root / "shared/src/iosMain/kotlin/org/example/taximobile/IosCurrentLocationRequester.kt").read_text(
        encoding="utf-8",
    )
    map_fab = (root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/MapFab.kt").read_text(
        encoding="utf-8",
    )
    success_confirmation = (root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/SuccessConfirmation.kt").read_text(
        encoding="utf-8",
    )

    require("class ConnectivityRecoveryPolicy" in common, "Shared reconnect policy is missing.")
    require("class ForegroundRecoveryPolicy" in common, "Shared foreground policy is missing.")
    require("state.hasAuthenticatedSession()" in common, "Offline failure must retain authenticated content.")
    require("suspend fun performAuthenticatedAction" in common,
            "Shared authenticated-action recovery is missing.")
    require("onBackendConfirmed" in common and "result !is AppUiState.Offline && result !is AppUiState.SignedOut" in common,
            "Only confirmed authenticated action results may emit success.")
    require(common.count("val result = action()") == 1,
            "Authenticated actions must execute exactly once in the shared recovery path.")
    require("val reconciled = accept(restore())" in common,
            "Uncertain authenticated actions must perform a read-only authoritative restore.")
    require("ACCESS_NETWORK_STATE" in manifest, "Android connectivity observation permission is missing.")
    require("registerDefaultNetworkCallback" in android_observer, "Android default-network observation is missing.")
    require("NET_CAPABILITY_VALIDATED" in android_observer, "Android must require a validated network.")
    require("nw_path_monitor_set_update_handler" in ios_observer, "iOS path observation is missing.")
    require("nw_path_status_satisfied" in ios_observer, "iOS must require a satisfied network path.")
    require("class AppActionGate" in action_model, "Shared double-submit gate is missing.")
    require("data class AppActionCompletion" in action_model and "val sequence: Long" in action_model,
            "Sequenced backend-confirmed action presentation is missing.")
    require("if (current != null) return false" in action_model,
            "The action gate must reject all overlapping operations.")
    require("class OneShotLocationGate" in location_gate and "if (inFlight) return false" in location_gate,
            "Shared foreground-location admission gate is missing.")
    for name, location_requester in (("Android", android_location), ("iOS", ios_location)):
        require("if (!requestGate.tryStart()) return" in location_requester,
                f"{name} repeated location requests must not cancel the active callback.")
        require("requestGate.finish()" in location_requester,
                f"{name} location admission gate is never released.")
    require("if (!enabled || loading) disabled()" in map_fab and "stateDescription = loadingDescription" in map_fab,
            "Map location controls must expose accessible disabled/loading state.")
    require("locationRequestInFlight" in passenger and "loading = locationRequestInFlight" in passenger,
            "Passenger one-shot location loading state is missing.")
    require("locationRequestInFlight" in driver and "loading = locationRequestInFlight" in driver,
            "Driver one-shot location loading state is missing.")
    require("if (current == null)" in driver and "onExpired()" in driver,
            "Malformed offer timing must request authoritative refresh.")
    require("acceptEnabled = countdown?.expired == false" in driver,
            "Malformed or expired offer timing must disable acceptance.")
    require("offer_timing_unavailable_refreshing" in driver,
            "Malformed offer timing needs an explicit localized presentation.")
    require("durationMillis = 320" in success_confirmation and "LiveRegionMode.Polite" in success_confirmation,
            "Confirmed actions need the documented accessible 320 ms success check.")
    require("rating_submitted_confirmation" in passenger,
            "Passenger rating confirmation is not rendered from backend completion.")
    require("cash_received_confirmation" in driver and "vehicle_registration_sent_confirmation" in driver,
            "Driver confirmed-action presentation is incomplete.")
    require("support_request_sent_confirmation" in shared_sections and "LaunchedEffect(completedAction?.sequence)" in shared_sections,
            "Confirmed support creation must render success and reset its draft.")
    require("pendingAction = pendingAction" in app,
            "Shared application root must propagate pending-action presentation state.")

    passenger_loading_actions = (
        "ESTIMATE_RIDE", "REQUEST_RIDE", "CANCEL_RIDE", "UPDATE_PASSENGER_PROFILE",
        "LOAD_PASSENGER_RIDE", "SUBMIT_RATING", "LOGOUT",
    )
    driver_loading_actions = (
        "SET_DRIVER_AVAILABILITY", "UPDATE_DRIVER_LOCATION", "REGISTER_DRIVER_VEHICLE",
        "SELECT_DRIVER_VEHICLE", "DEACTIVATE_DRIVER_VEHICLE", "RESPOND_TO_OFFER",
        "ADVANCE_DRIVER_RIDE", "CANCEL_DRIVER_RIDE", "COMPLETE_DRIVER_RIDE",
        "SETTLE_DRIVER_CASH", "LOAD_DRIVER_RIDE", "LOGOUT",
    )
    for action in passenger_loading_actions:
        require(f"pendingAction.isPending(AppActionKind.{action}" in passenger,
                f"Passenger action {action} has no exact loading presentation.")
    for action in driver_loading_actions:
        require(f"pendingAction.isPending(AppActionKind.{action}" in driver,
                f"Driver action {action} has no exact loading presentation.")
    for action in ("APPLY_TO_DRIVE", "SUBMIT_DRIVER_VERIFICATION"):
        require(f"pendingAction.isPending(AppActionKind.{action}" in screen,
                f"Driver onboarding action {action} has no loading presentation.")
    for action in ("CREATE_SUPPORT_TICKET", "MARK_NOTIFICATION_READ"):
        require(f"pendingAction.isPending(AppActionKind.{action}" in shared_sections,
                f"Shared action {action} has no exact loading presentation.")

    for name, platform_root in (("Android", android_root), ("iOS", ios_root)):
        require("Lifecycle.Event.ON_STOP" in platform_root, f"{name} background transition is missing.")
        require("Lifecycle.Event.ON_START" in platform_root, f"{name} foreground transition is missing.")
        require("shouldRefreshOnForeground()" in platform_root, f"{name} foreground policy is not applied.")
        require("hasAuthenticatedSession()" in platform_root, f"{name} foreground refresh must require a session.")
        require("presentation.accept(dependencies.appCoordinator.restore())" in platform_root,
                f"{name} recovery must use retained authoritative presentation.")
        require("fun submitAction(" in platform_root,
                f"{name} synchronously gated action helper is missing.")
        require("restore = dependencies.appCoordinator::restore" in platform_root,
                f"{name} failed actions must reconcile through a read-only restore.")
        require("completedAction = AppActionCompletion(completionSequence, key)" in platform_root,
                f"{name} does not publish sequenced backend-confirmed action completion.")
        helper = platform_root[platform_root.index("fun submitAction("):]
        require("if (!actionGate.tryStart(key)) return" in helper,
                f"{name} actions are not rejected synchronously while one is active.")
        require(helper.index("if (!actionGate.tryStart(key)) return") < helper.index("scope.launch"),
                f"{name} action gate must run before launching the coroutine.")
        require("finally" in helper and "actionGate.finish(key)" in helper and "pendingAction = actionGate.current" in helper,
                f"{name} action gate is not reliably released.")

        authenticated_actions = (
            ("SET_DRIVER_AVAILABILITY", "changeDriverAvailability"),
            ("UPDATE_DRIVER_LOCATION", "updateDriverLocation"),
            ("REGISTER_DRIVER_VEHICLE", "registerDriverVehicle"),
            ("SELECT_DRIVER_VEHICLE", "selectDriverVehicle"),
            ("DEACTIVATE_DRIVER_VEHICLE", "deactivateDriverVehicle"),
            ("ESTIMATE_RIDE", "estimateRide"), ("REQUEST_RIDE", "requestRide"),
            ("CANCEL_RIDE", "cancelRide"), ("LOAD_PASSENGER_RIDE", "loadPassengerRideHistoryDetail"),
            ("LOAD_DRIVER_RIDE", "loadDriverRideHistoryDetail"),
            ("UPDATE_PASSENGER_PROFILE", "updatePassengerProfile"),
            ("SUBMIT_RATING", "submitRideRating"), ("CREATE_SUPPORT_TICKET", "createSupportTicket"),
            ("RESPOND_TO_OFFER", "respondToOffer"), ("ADVANCE_DRIVER_RIDE", "advanceDriverRide"),
            ("CANCEL_DRIVER_RIDE", "cancelDriverRide"), ("COMPLETE_DRIVER_RIDE", "completeDriverRide"),
            ("SETTLE_DRIVER_CASH", "settleDriverCash"), ("APPLY_TO_DRIVE", "applyToDrive"),
            ("SUBMIT_DRIVER_VERIFICATION", "submitDriverVerification"),
            ("MARK_NOTIFICATION_READ", "markNotificationRead"),
        )
        for action_kind, coordinator_call in authenticated_actions:
            require(f"submitAction(AppAction(AppActionKind.{action_kind}" in platform_root,
                    f"{name} action {action_kind} bypasses the synchronous gate.")
            require(f"dependencies.appCoordinator.{coordinator_call}" in platform_root,
                    f"{name} action {coordinator_call} is disconnected from its coordinator.")


if __name__ == "__main__":
    validate_mobile_recovery()
    print("Validated Android/iOS connectivity, foreground, command, and one-shot location recovery gates.")
