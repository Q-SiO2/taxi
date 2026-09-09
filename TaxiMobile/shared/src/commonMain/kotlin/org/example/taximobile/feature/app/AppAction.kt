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
    LOAD_ACCOUNT_SECURITY,
    CREATE_RECOVERY_CODES,
    REVOKE_ACCOUNT_SESSION,
    CHANGE_ACCOUNT_PASSWORD,
    APPLY_TO_DRIVE,
    SUBMIT_DRIVER_VERIFICATION,
    CREATE_DRIVER_CITY_APPLICATION,
    SELECT_DRIVER_CITY_APPLICATION,
    SAVE_DRIVER_CITY_APPLICATION,
    SUBMIT_DRIVER_CITY_APPLICATION,
    WITHDRAW_DRIVER_CITY_APPLICATION,
    UPLOAD_DRIVER_APPLICATION_DOCUMENT,
    DELETE_DRIVER_APPLICATION_DOCUMENT,
    REGISTER_APPLICANT_VEHICLE,
    SET_DRIVER_AVAILABILITY,
    UPDATE_DRIVER_LOCATION,
    REGISTER_DRIVER_VEHICLE,
    SELECT_DRIVER_VEHICLE,
    DEACTIVATE_DRIVER_VEHICLE,
    SEARCH_PLACES,
    REVERSE_PLACE,
    ESTIMATE_RIDE,
    REQUEST_RIDE,
    LOAD_FIXED_ROUTES,
    ESTIMATE_FIXED_ROUTE,
    REQUEST_FIXED_ROUTE,
    ESTIMATE_SCHEDULED_BOOKING,
    CREATE_SCHEDULED_BOOKING,
    CANCEL_SCHEDULED_BOOKING,
    SET_SCHEDULED_OFFER_PREFERENCE,
    RESPOND_TO_SCHEDULED_OFFER,
    SUBMIT_MANUAL_TRANSFER,
    CANCEL_RIDE,
    SEND_RIDE_COORDINATION,
    LOAD_PASSENGER_RIDE,
    LOAD_DRIVER_RIDE,
    UPDATE_PASSENGER_PROFILE,
    SUBMIT_RATING,
    CREATE_SUPPORT_TICKET,
    CREATE_SAFETY_REPORT,
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
