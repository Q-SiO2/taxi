package org.example.taximobile.feature.rides

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import org.example.taximobile.domain.rides.RideCoordinationCode
import org.example.taximobile.domain.rides.RideCoordinationMessage
import org.example.taximobile.domain.rides.RideCoordinationSenderRole
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.isPending
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.components.TaxiCard
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.jetbrains.compose.resources.StringResource
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

private val PASSENGER_ACTIONS = listOf(
    RideCoordinationCode.PASSENGER_AT_PICKUP,
    RideCoordinationCode.PASSENGER_NEEDS_MORE_TIME,
    RideCoordinationCode.PASSENGER_CANNOT_FIND_DRIVER,
)

private val DRIVER_ACTIONS = listOf(
    RideCoordinationCode.DRIVER_ON_MY_WAY,
    RideCoordinationCode.DRIVER_AT_PICKUP,
    RideCoordinationCode.DRIVER_CANNOT_FIND_PASSENGER,
)

@Composable
internal fun RideLatestCoordinationMessage(message: RideCoordinationMessage?) {
    if (message == null) return
    TaxiCard {
        Text(
            stringResource(Res.string.latest_ride_coordination_update),
            style = MaterialTheme.typography.labelLarge,
            color = TaxiColors.Ink500,
        )
        Text(
            stringResource(message.code.copyResource()),
            style = MaterialTheme.typography.bodyLarge,
        )
    }
}

@Composable
internal fun RideCoordinationActions(
    rideId: String,
    senderRole: RideCoordinationSenderRole,
    pendingAction: AppAction?,
    onSend: (String, RideCoordinationCode) -> Unit,
    modifier: Modifier = Modifier,
) {
    val actions = when (senderRole) {
        RideCoordinationSenderRole.PASSENGER -> PASSENGER_ACTIONS
        RideCoordinationSenderRole.DRIVER -> DRIVER_ACTIONS
        RideCoordinationSenderRole.UNKNOWN -> emptyList()
    }
    if (actions.isEmpty()) return
    TaxiCard(modifier) {
        Text(
            stringResource(Res.string.ride_coordination_title),
            style = MaterialTheme.typography.titleMedium,
        )
        Text(
            stringResource(Res.string.ride_coordination_help),
            style = MaterialTheme.typography.bodySmall,
            color = TaxiColors.Ink500,
        )
        actions.forEach { code ->
            TaxiButton(
                label = stringResource(code.copyResource()),
                onClick = { onSend(rideId, code) },
                enabled = pendingAction == null,
                loading = pendingAction.isPending(
                    AppActionKind.SEND_RIDE_COORDINATION,
                    "$rideId:${code.name}",
                ),
                style = TaxiButtonStyle.Tertiary,
            )
        }
    }
}

internal fun RideCoordinationCode.copyResource(): StringResource = when (this) {
    RideCoordinationCode.PASSENGER_AT_PICKUP -> Res.string.ride_update_passenger_at_pickup
    RideCoordinationCode.PASSENGER_NEEDS_MORE_TIME -> Res.string.ride_update_passenger_needs_more_time
    RideCoordinationCode.PASSENGER_CANNOT_FIND_DRIVER -> Res.string.ride_update_passenger_cannot_find_driver
    RideCoordinationCode.DRIVER_ON_MY_WAY -> Res.string.ride_update_driver_on_my_way
    RideCoordinationCode.DRIVER_AT_PICKUP -> Res.string.ride_update_driver_at_pickup
    RideCoordinationCode.DRIVER_CANNOT_FIND_PASSENGER -> Res.string.ride_update_driver_cannot_find_passenger
    RideCoordinationCode.UNKNOWN -> Res.string.ride_update_unavailable
}
