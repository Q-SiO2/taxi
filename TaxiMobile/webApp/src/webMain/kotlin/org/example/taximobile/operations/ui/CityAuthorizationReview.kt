package org.example.taximobile.operations.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.text.style.TextDirection
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.example.taximobile.feature.ui.theme.TaxiTheme
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.CityAuthorizationAction
import org.example.taximobile.operations.model.OperationsCityApplicationRecord
import org.example.taximobile.operations.model.cityAuthorizationActions
import org.example.taximobile.operations.state.OperationsCoordinator
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

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
        SectionHeading(stringResource(Res.string.web_auth_title), stringResource(Res.string.web_auth_scope, ltrIsolate(application.cityCode)))
        StatusBadge(authorization.status, label = recruitmentLabel(authorization.status))
        Text(stringResource(Res.string.web_auth_until, authorization.validUntil?.let(::ltrIsolate) ?: stringResource(Res.string.web_auth_no_expiry)))
        Text(stringResource(Res.string.web_auth_history_notice))
        cityAuthorizationActions(authorization.status).forEach { action ->
            OutlinedButton(shape = RoundedCornerShape(TaxiTheme.radii.Md), onClick = { pending = action }, enabled = !locked) { Text(recruitmentLabel(action.name)) }
        }
        if (authorization.status == "REVOKED") Text(stringResource(Res.string.web_auth_new_application))
    }
    pending?.let { action ->
        var reason by remember(authorization.id, action) { mutableStateOf(action.reasons.first()) }
        var confirmation by remember(authorization.id, action) { mutableStateOf("") }
        AlertDialog(
            shape = RoundedCornerShape(TaxiTheme.radii.Lg),
            onDismissRequest = { if (!locked) pending = null },
            title = { Text(stringResource(Res.string.web_auth_question, recruitmentLabel(action.name))) },
            text = {
                Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    Text(stringResource(Res.string.web_auth_scope, ltrIsolate(application.cityCode)))
                    Text(stringResource(Res.string.web_auth_id, ltrIsolate(authorization.id)))
                    Text(stringResource(if (action == CityAuthorizationAction.REINSTATE)
                        Res.string.web_auth_reinstate_notice else Res.string.web_auth_block_notice))
                    Text(stringResource(Res.string.web_recruit_review_reason))
                    action.reasons.forEach { value ->
                        TextButton(onClick = { reason = value }, enabled = !locked) {
                            Text(if (reason == value) stringResource(Res.string.web_auth_selected_reason, recruitmentLabel(value)) else recruitmentLabel(value))
                        }
                    }
                    OutlinedTextField(confirmation, { confirmation = it }, Modifier.fillMaxWidth(),
                        label = { Text(stringResource(Res.string.web_auth_type_id)) }, singleLine = true, enabled = !locked,
                        textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr))
                }
            },
            confirmButton = {
                Button(shape = RoundedCornerShape(TaxiTheme.radii.Md), onClick = {
                    coordinator.decideCityAuthorization(authorization.id, application.optimisticVersion,
                        action, reason, confirmation)
                    pending = null
                }, enabled = !locked && confirmation.trim() == authorization.id) { Text(stringResource(Res.string.web_auth_confirm, recruitmentLabel(action.name))) }
            },
            dismissButton = { TextButton(onClick = { pending = null }, enabled = !locked) { Text(stringResource(Res.string.web_cancel)) } },
        )
    }
}
