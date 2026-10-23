package org.example.taximobile.operations.ui

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.theme.TaxiTheme
import org.example.taximobile.operations.model.*
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsUiState
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*
import kotlin.random.Random
import kotlin.time.Clock

@Composable
internal fun OperatorMembershipPanel(operator: OperatorRecord, state: OperationsUiState, coordinator: OperationsCoordinator) {
    if (state.session?.hasPermission(MANAGE_OPERATORS) != true) return
    val colors = TaxiTheme.colors
    val page = state.operatorMemberships?.takeIf { it.operatorId == operator.id && it.cooperativeId == operator.cooperativeId }
    var enrolling by remember(operator.id) { mutableStateOf(false) }
    var editing by remember(operator.id) { mutableStateOf<OperatorMembershipRecord?>(null) }
    var reviewingPolicy by remember(operator.id) { mutableStateOf(false) }
    LaunchedEffect(page?.items, editing?.id) {
        val reviewed = editing
        val latest = page?.items?.firstOrNull { it.id == reviewed?.id }
        if (reviewed != null && latest != null && latest.updatedAt != reviewed.updatedAt) editing = null
    }
    DataCard {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
            Text(stringResource(Res.string.web_members_title), style = MaterialTheme.typography.titleLarge)
            Text(stringResource(if (operator.requiresActiveMembership) Res.string.web_members_required else Res.string.web_members_open))
            Text(stringResource(Res.string.web_members_policy_help), color = colors.Ink500)
            if (operator.cooperativeId == null) {
                Text(stringResource(Res.string.web_members_scope), color = colors.Ink500)
            } else {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    OutlinedButton(shape = RoundedCornerShape(TaxiTheme.radii.Md), onClick = { reviewingPolicy = true }, enabled = !state.interactionLocked) {
                        Text(stringResource(if (operator.requiresActiveMembership) Res.string.web_members_disable else Res.string.web_members_enable))
                    }
                    OutlinedButton(shape = RoundedCornerShape(TaxiTheme.radii.Md), onClick = { coordinator.loadOperatorMemberships(page?.page ?: 1) }, enabled = !state.interactionLocked) {
                        Text(stringResource(if (page == null) Res.string.web_members_load else Res.string.web_members_refresh))
                    }
                    Button(shape = RoundedCornerShape(TaxiTheme.radii.Md), onClick = { enrolling = true }, enabled = !state.interactionLocked) {
                        Text(stringResource(Res.string.web_members_add))
                    }
                }
                if (page != null) {
                    if (page.cooperativeStatus != "ACTIVE" && operator.requiresActiveMembership) Text(stringResource(Res.string.web_members_inactive), color = colors.Danger600)
                    if (page.items.isEmpty()) Text(stringResource(Res.string.web_members_empty), color = colors.Ink500)
                    page.items.forEach { member ->
                        Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                            SelectionContainer {
                                Text("${stringResource(Res.string.web_members_driver)} · ${ltrIsolate(member.driverId ?: "—")}")
                            }
                            Text("${membershipStatusLabel(member.status)} · ${member.membershipNumber ?: "—"}")
                            member.joinedAt?.let { Text("${stringResource(Res.string.web_members_joined)} · ${ltrIsolate(it)}", style = MaterialTheme.typography.bodySmall) }
                            member.endedAt?.let { Text("${stringResource(Res.string.web_members_until)} · ${ltrIsolate(it)}", style = MaterialTheme.typography.bodySmall) }
                            TextButton(onClick = { editing = member }, enabled = !state.interactionLocked) { Text(stringResource(Res.string.web_members_edit)) }
                        }
                    }
                    Text(stringResource(Res.string.web_members_page, page.page, page.total))
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                        OutlinedButton(shape = RoundedCornerShape(TaxiTheme.radii.Md), onClick = { coordinator.loadOperatorMemberships(page.page - 1) }, enabled = !state.interactionLocked && page.page > 1) { Text(stringResource(Res.string.web_members_previous)) }
                        OutlinedButton(shape = RoundedCornerShape(TaxiTheme.radii.Md), onClick = { coordinator.loadOperatorMemberships(page.page + 1) }, enabled = !state.interactionLocked && page.page.toLong() * page.limit < page.total) { Text(stringResource(Res.string.web_members_next)) }
                    }
                }
            }
        }
    }
    if (enrolling || editing != null) {
        MembershipEditor(
            member = editing, busy = state.interactionLocked, completedKey = state.membershipCompletedKey,
            candidates = state.snapshot?.driverApplications?.items.orEmpty().map { it.driverId to it.displayName }.distinctBy { it.first },
            onDismiss = { enrolling = false; editing = null },
            onSave = { driver, status, number, joined, ended, reason, key ->
                val member = editing
                if (member == null) coordinator.enrollOperatorMember(
                    OperatorMembershipCreateRequest(driver, status, number, joined, ended, reason), key,
                ) else coordinator.updateOperatorMember(
                    member, OperatorMembershipUpdateRequest(status, number, joined, ended, member.updatedAt, reason), key,
                )
            },
        )
    }
    if (reviewingPolicy) {
        AlertDialog(
            onDismissRequest = { if (!state.interactionLocked) reviewingPolicy = false },
            title = { Text(stringResource(Res.string.web_members_policy_review)) },
            text = { Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text(stringResource(if (operator.requiresActiveMembership) Res.string.web_members_disable else Res.string.web_members_enable))
                Text(stringResource(Res.string.web_members_policy_help))
            } },
            confirmButton = { Button(shape = RoundedCornerShape(TaxiTheme.radii.Md), onClick = { reviewingPolicy = false; coordinator.updateOperatorMembershipPolicy(!operator.requiresActiveMembership) }, enabled = !state.interactionLocked) { Text(stringResource(Res.string.web_members_save)) } },
            dismissButton = { TextButton(onClick = { reviewingPolicy = false }, enabled = !state.interactionLocked) { Text(stringResource(Res.string.web_members_cancel)) } },
        )
    }
}

@Composable
private fun MembershipEditor(
    member: OperatorMembershipRecord?, busy: Boolean, completedKey: String?, candidates: List<Pair<String, String>>, onDismiss: () -> Unit,
    onSave: (String, String, String?, String?, String?, String, String) -> Unit,
) {
    var driverId by remember(member?.id) { mutableStateOf(member?.driverId.orEmpty()) }
    var status by remember(member?.id) { mutableStateOf(member?.status ?: "PENDING") }
    var number by remember(member?.id) { mutableStateOf(member?.membershipNumber.orEmpty()) }
    var joined by remember(member?.id) { mutableStateOf(member?.joinedAt.orEmpty()) }
    var ended by remember(member?.id) { mutableStateOf(member?.endedAt.orEmpty()) }
    var reason by remember(member?.id) { mutableStateOf("") }
    var submittedKey by remember { mutableStateOf<String?>(null) }
    var choosingDriver by remember { mutableStateOf(false) }
    // The same reviewed payload keeps its key through a failed/unknown response.
    // Editing the payload creates a new command; no implicit replay follows MFA.
    val key = remember(driverId, status, number, joined, ended, reason) {
        "member-${Clock.System.now().toEpochMilliseconds()}-${Random.nextInt(100000, 999999)}"
    }
    LaunchedEffect(completedKey) { if (completedKey != null && completedKey == submittedKey) onDismiss() }
    val valid = (member != null || validMembershipDriverId(driverId)) && reason.trim().length in 3..240 && validMembershipDates(joined, ended)
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text(stringResource(if (member == null) Res.string.web_members_add else Res.string.web_members_edit)) },
        text = { Column(Modifier.fillMaxWidth().heightIn(max = 520.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            Text(stringResource(Res.string.web_members_help))
            if (member == null) {
                if (candidates.isNotEmpty()) {
                    OutlinedButton(shape = RoundedCornerShape(TaxiTheme.radii.Md), onClick = { choosingDriver = true }, enabled = !busy) { Text(stringResource(Res.string.web_members_driver)) }
                    DropdownMenu(expanded = choosingDriver, onDismissRequest = { choosingDriver = false }) {
                        candidates.forEach { (id, name) -> DropdownMenuItem(text = { Text(name) }, onClick = { driverId = id; choosingDriver = false }) }
                    }
                }
                MembershipField(driverId, { driverId = it.take(36) }, stringResource(Res.string.web_members_driver), busy, ltr = true)
                Text(stringResource(Res.string.web_members_driver_help), style = MaterialTheme.typography.bodySmall)
            }
            Text(stringResource(Res.string.web_members_status))
            (if (member == null) listOf("PENDING", "ACTIVE") else listOf("PENDING", "ACTIVE", "SUSPENDED", "ENDED")).forEach { option ->
                Row {
                    RadioButton(selected = status == option, onClick = { status = option }, enabled = !busy)
                    Text(membershipStatusLabel(option), modifier = Modifier.padding(top = 12.dp))
                }
            }
            MembershipField(number, { number = it.take(120) }, stringResource(Res.string.web_members_number), busy)
            MembershipField(joined, { joined = it.take(40) }, stringResource(Res.string.web_members_joined), busy, ltr = true)
            MembershipField(ended, { ended = it.take(40) }, stringResource(Res.string.web_members_until), busy, ltr = true)
            if (!validMembershipDates(joined, ended)) Text(stringResource(Res.string.web_members_date_error), color = TaxiTheme.colors.Danger600)
            Text(stringResource(Res.string.web_members_dates_help), style = MaterialTheme.typography.bodySmall)
            MembershipField(reason, { reason = it.take(240) }, stringResource(Res.string.web_members_reason), busy)
            Text(stringResource(Res.string.web_members_reason_help), style = MaterialTheme.typography.bodySmall)
        } },
        confirmButton = { Button(shape = RoundedCornerShape(TaxiTheme.radii.Md), onClick = { submittedKey = key; onSave(driverId.trim(), status, number.trim().ifEmpty { null }, joined.trim().ifEmpty { null }, ended.trim().ifEmpty { null }, reason.trim(), key) }, enabled = !busy && valid) { Text(stringResource(Res.string.web_members_save)) } },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text(stringResource(Res.string.web_members_cancel)) } },
    )
}

@Composable
private fun MembershipField(value: String, onChange: (String) -> Unit, label: String, busy: Boolean, ltr: Boolean = false) {
    OutlinedTextField(value = value, onValueChange = onChange, label = { Text(label) }, enabled = !busy, singleLine = true,
        textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = if (ltr) TextDirection.Ltr else TextDirection.Content), modifier = Modifier.fillMaxWidth())
}

@Composable
private fun membershipStatusLabel(status: String): String = stringResource(when (status) {
    "ACTIVE" -> Res.string.web_members_active
    "SUSPENDED" -> Res.string.web_members_suspended
    "ENDED" -> Res.string.web_members_ended
    else -> Res.string.web_members_pending
})

@Composable
internal fun membershipMutationLabel(label: String): String = when (label) {
    "Loading member register" -> stringResource(Res.string.web_members_loading)
    "Recording membership", "Updating membership" -> stringResource(Res.string.web_members_saving)
    "Updating membership policy" -> stringResource(Res.string.web_members_policy_saving)
    else -> stringResource(Res.string.web_pending_action)
}
