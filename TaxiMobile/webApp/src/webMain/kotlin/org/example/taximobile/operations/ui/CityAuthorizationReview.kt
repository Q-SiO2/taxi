package org.example.taximobile.operations.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.CityAuthorizationAction
import org.example.taximobile.operations.model.OperationsCityApplicationRecord
import org.example.taximobile.operations.model.cityAuthorizationActions
import org.example.taximobile.operations.state.OperationsCoordinator

@Composable
internal fun CityAuthorizationReview(
    application: OperationsCityApplicationRecord,
    locked: Boolean,
    coordinator: OperationsCoordinator,
) {
    val authorization = application.authorization ?: return
    var pending by remember(authorization.id, application.optimisticVersion) {
        mutableStateOf<CityAuthorizationAction?>(null)
    }
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        SectionHeading("City authorization", "Decisions apply to ${application.cityCode} only.")
        StatusBadge(authorization.status)
        Text("Valid until: ${authorization.validUntil ?: "No recorded expiry"}")
        Text("Existing rides and commitments keep their history. New work must pass the current eligibility checks.")
        cityAuthorizationActions(authorization.status).forEach { action ->
            OutlinedButton(onClick = { pending = action }, enabled = !locked) { Text(action.label) }
        }
        if (authorization.status == "REVOKED") Text("A new application is required after revocation.")
    }
    pending?.let { action ->
        var reason by remember(authorization.id, action) { mutableStateOf(action.reasons.first()) }
        var confirmation by remember(authorization.id, action) { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { if (!locked) pending = null },
            title = { Text("${action.label} city authorization?") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    Text("City: ${application.cityCode}")
                    Text("Authorization: ${authorization.id}")
                    Text(if (action == CityAuthorizationAction.REINSTATE)
                        "The backend will recheck eligibility. Reinstatement does not extend the expiry or put the driver online."
                    else "New assignments in this city will be blocked after this decision. Handle existing rides through the normal support workflow.")
                    Text("Review reason")
                    action.reasons.forEach { value ->
                        TextButton(onClick = { reason = value }, enabled = !locked) {
                            Text((if (reason == value) "Selected: " else "") + value.replace('_', ' '))
                        }
                    }
                    OutlinedTextField(confirmation, { confirmation = it }, Modifier.fillMaxWidth(),
                        label = { Text("Type the full authorization ID") }, singleLine = true, enabled = !locked)
                }
            },
            confirmButton = {
                Button(onClick = {
                    coordinator.decideCityAuthorization(authorization.id, application.optimisticVersion,
                        action, reason, confirmation)
                    pending = null
                }, enabled = !locked && confirmation.trim() == authorization.id) { Text("Confirm ${action.label.lowercase()}") }
            },
            dismissButton = { TextButton(onClick = { pending = null }, enabled = !locked) { Text("Cancel") } },
        )
    }
}
