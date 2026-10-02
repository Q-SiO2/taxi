"""Source-wiring gate; shared behavior tests and physical acceptance remain separate."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
COMMON = "shared/src/commonMain/kotlin/org/example/taximobile/"
SOURCES = {
    "android": "androidApp/src/main/kotlin/org/example/taximobile/MainActivity.kt",
    "ios": "shared/src/iosMain/kotlin/org/example/taximobile/MainViewController.kt",
    "subscription": COMMON + "feature/realtime/LiveUpdateSubscription.kt",
    "gateway": COMMON + "data/realtime/KtorLiveEventGateway.kt",
    "authentication": COMMON + "feature/auth/AuthenticationSessionCoordinator.kt",
    "lifetime": COMMON + "feature/auth/LocalSessionLifetime.kt",
    "coordinator": COMMON + "feature/app/MobileAppCoordinator.kt",
}


class LiveUpdateConfigurationError(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise LiveUpdateConfigurationError(reason)


def require_order(source: str, before: str, after: str, reason: str) -> None:
    require(before in source and after in source and source.index(before) < source.index(after), reason)


def validate_mobile_live_updates(root: Path = ROOT) -> None:
    try:
        code = {
            name: re.sub(r"/\*.*?\*/|//[^\n]*", "", (root / relative).read_text(encoding="utf-8"), flags=re.S)
            for name, relative in SOURCES.items()
        }
    except OSError as error:
        raise LiveUpdateConfigurationError("Required live-update source is missing or unreadable") from error

    subscription = code["subscription"]
    for required in (
        "foreground && connectivity != ConnectivityStatus.UNAVAILABLE",
        "AppActionKind.LOGOUT", "AppActionKind.REVOKE_ACCOUNT_SESSION", "AppActionKind.CHANGE_ACCOUNT_PASSWORD",
        "lifetime.collectLatest", "if (!owner.active)", "while (lifetime.value == owner)",
        "if (lifetime.value != owner) return", "ownership.withLock", "waitForRetry(retry.nextDelayMillis())",
        "withTimeoutOrNull(connectTimeoutMillis)", "withTimeoutOrNull(refreshTimeoutMillis)",
        "socket.cancelAndJoin()", "catch (error: CancellationException)", "throw error",
    ):
        require(required in subscription, f"Shared live-update ownership/recovery is missing: {required}")

    gateway = code["gateway"]
    require("catch (error: CancellationException)" in gateway, "Ktor cancellation must propagate")
    require_order(gateway, "catch (error: CancellationException)", "catch (error: Exception)",
                  "Cancellation must precede generic transport normalization")
    require_order(gateway, "onConnected()", "for (frame in incoming)",
                  "REST catch-up must start after socket admission and before frame consumption")

    authentication = code["authentication"]
    for required in ("StateFlow<LocalSessionLifetime>", "mutableLifetime.asStateFlow()", "sessionMutex.withLock",
                     "stopLiveUpdates()", "sessionAvailable(replaced = true)",
                     "ending = true", "!current.ending"):
        require(required in authentication, f"Credential-generation ownership is missing: {required}")
    require(all(field in code["lifetime"] for field in
                ("val generation: Long", "val active: Boolean", "val ending: Boolean")),
            "Subscription lifetime must contain only non-secret generation and lifecycle flags")
    require("String" not in code["lifetime"] and "StoredTokens" not in code["lifetime"],
            "Credentials and identity must not enter subscription render keys")
    require("liveSubscription?.run(onRefresh)" in code["coordinator"], "Mobile coordinator must use the shared supervisor")
    require("suspend fun logout(): AppUiState" in code["coordinator"], "Mobile logout boundary is missing")
    logout = code["coordinator"].split("suspend fun logout(): AppUiState", 1)[1].split("suspend fun login", 1)[0]
    require_order(logout, "authentication.beginSessionEnd()", "revokeRegisteredPushRegistration()",
                  "Logout must stop hints before awaiting push cleanup")

    for name in ("android", "ios"):
        source = code[name]
        require("val liveUpdatesEnabled = canListenForLiveUpdates(" in source,
                f"{name} must derive foreground/network/security-command ownership")
        require("LaunchedEffect(dependencies, liveUpdatesEnabled)" in source,
                f"{name} listener effect must restart when ownership changes")
        require("LaunchedEffect(presentation.state is AppUiState.PassengerReady" not in source,
                f"{name} must not retain the old ready-category-only effect")
        effect = source.split("LaunchedEffect(dependencies, liveUpdatesEnabled)", 1)[1].split("App(", 1)[0]
        for required in ("if (liveUpdatesEnabled)", "listenForLiveUpdates", "return@listenForLiveUpdates",
                         "val owner = dependencies.appCoordinator.liveSessionLifetime.value",
                         "val restored = dependencies.appCoordinator.restore()",
                         "currentCoroutineContext().ensureActive()",
                         "owner == dependencies.appCoordinator.liveSessionLifetime.value",
                         "presentation = presentation.accept(restored)"):
            require(required in effect, f"{name} callback ownership/reconciliation is missing: {required}")
        require(effect.index("currentCoroutineContext().ensureActive()") < effect.index("presentation = presentation.accept(restored)"),
                f"{name} must reject cancelled catch-up before applying render state")


if __name__ == "__main__":
    validate_mobile_live_updates()
    print("Validated mobile live-update session, lifecycle, cancellation and reconnect source wiring.")
