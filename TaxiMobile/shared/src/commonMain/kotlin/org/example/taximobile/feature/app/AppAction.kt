package org.example.taximobile.feature.app

/**
 * A user-initiated operation whose completion must be confirmed by the backend.
 * [resourceId] distinguishes controls that repeat in a list without exposing the
 * identifier outside in-memory presentation state.
 */
data class AppAction(
    val kind: AppActionKind,
    val resourceId: String? = null,
)

/** Monotonic event emitted only after a coordinator returns confirmed state. */
data class AppActionCompletion(
    val sequence: Long,
    val action: AppAction,
)

enum class AppActionKind {
    REFRESH,
    LOGOUT,
    APPLY_TO_DRIVE,
    SUBMIT_DRIVER_VERIFICATION,
    SET_DRIVER_AVAILABILITY,
    UPDATE_DRIVER_LOCATION,
    REGISTER_DRIVER_VEHICLE,
    SELECT_DRIVER_VEHICLE,
    DEACTIVATE_DRIVER_VEHICLE,
    ESTIMATE_RIDE,
    REQUEST_RIDE,
    CANCEL_RIDE,
    LOAD_PASSENGER_RIDE,
    LOAD_DRIVER_RIDE,
    UPDATE_PASSENGER_PROFILE,
    SUBMIT_RATING,
    CREATE_SUPPORT_TICKET,
    RESPOND_TO_OFFER,
    ADVANCE_DRIVER_RIDE,
    CANCEL_DRIVER_RIDE,
    COMPLETE_DRIVER_RIDE,
    SETTLE_DRIVER_CASH,
    MARK_NOTIFICATION_READ,
}

/**
 * Synchronous admission gate used before launching a coroutine. This closes the
 * tap-to-coroutine race: a second callback cannot start while the first command
 * is suspended, even before Compose has rendered the loading state.
 */
class AppActionGate {
    var current: AppAction? = null
        private set

    fun tryStart(action: AppAction): Boolean {
        if (current != null) return false
        current = action
        return true
    }

    fun finish(action: AppAction) {
        if (current == action) current = null
    }
}

fun AppAction?.isPending(kind: AppActionKind, resourceId: String? = null): Boolean =
    this?.kind == kind && this.resourceId == resourceId

fun AppActionCompletion?.confirms(kind: AppActionKind, resourceId: String? = null): Boolean =
    this?.action?.kind == kind && this.action.resourceId == resourceId
