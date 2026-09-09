package org.example.taximobile.feature.account

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.testTag
import org.example.taximobile.domain.auth.AccountSession
import org.example.taximobile.feature.app.AccountSecurityUiState
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.isPending
import org.example.taximobile.feature.ui.components.ConfirmDialog
import org.example.taximobile.feature.ui.components.PasswordField
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.components.TaxiCard
import org.example.taximobile.feature.ui.components.ToastBanner
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.example.taximobile.feature.ui.text.resolve
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

/** Shared passenger/driver account controls; the backend remains authoritative. */
@Composable
fun AccountSecuritySection(
    state: AccountSecurityUiState,
    pendingAction: AppAction?,
    onLoad: () -> Unit,
    onCreateRecoveryCodes: (String) -> Unit,
    onAcknowledgeRecoveryCodes: () -> Unit,
    onRevokeSession: (String) -> Unit,
    onChangePassword: (String, String) -> Unit,
) {
    var recoveryPassword by remember { mutableStateOf("") }
    var currentPassword by remember { mutableStateOf("") }
    var newPassword by remember { mutableStateOf("") }
    var sessionToRevoke by remember { mutableStateOf<AccountSession?>(null) }
    var recoveryCodesSaved by remember(state.recoveryCodes) { mutableStateOf(false) }

    LaunchedEffect(state.loaded) {
        if (!state.loaded) onLoad()
    }
    LaunchedEffect(state.recoveryCodes) {
        if (state.recoveryCodes != null) recoveryPassword = ""
    }

    Text(stringResource(Res.string.account_security), style = MaterialTheme.typography.titleLarge)
    state.message?.let {
        ToastBanner(
            it.resolve(),
            if (state.recoveryCodes != null) StatusTone.Success else StatusTone.Warning,
        )
    }

    Text(stringResource(Res.string.active_sessions), style = MaterialTheme.typography.titleMedium)
    when {
        pendingAction.isPending(AppActionKind.LOAD_ACCOUNT_SECURITY) ->
            Text(stringResource(Res.string.loading_account_security))
        state.loaded && state.sessions.isEmpty() ->
            Text(stringResource(Res.string.no_active_sessions))
        else -> state.sessions.forEach { session ->
            TaxiCard(Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(TaxiSpacing.Md),
                    verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
                ) {
                    Text(
                        session.deviceLabel?.takeIf(String::isNotBlank)
                            ?: stringResource(Res.string.unknown_device),
                        style = MaterialTheme.typography.titleSmall,
                    )
                    if (session.current) Text(stringResource(Res.string.current_session))
                    Text(stringResource(Res.string.session_created, ltrIsolate(session.createdAt)))
                    Text(stringResource(Res.string.session_expires, ltrIsolate(session.expiresAt)))
                    TaxiButton(
                        label = if (session.current) {
                            stringResource(Res.string.sign_out_this_session)
                        } else {
                            stringResource(Res.string.revoke_session)
                        },
                        onClick = { sessionToRevoke = session },
                        enabled = pendingAction == null,
                        loading = pendingAction.isPending(
                            AppActionKind.REVOKE_ACCOUNT_SESSION,
                            session.id,
                        ),
                        style = TaxiButtonStyle.Tertiary,
                    )
                }
            }
        }
    }

    Text(stringResource(Res.string.offline_recovery_codes), style = MaterialTheme.typography.titleMedium)
    Text(stringResource(Res.string.recovery_codes_explanation))
    PasswordField(
        recoveryPassword,
        { recoveryPassword = it },
        stringResource(Res.string.current_password),
    )
    TaxiButton(
        label = stringResource(Res.string.create_new_recovery_codes),
        onClick = { onCreateRecoveryCodes(recoveryPassword) },
        enabled = recoveryPassword.isNotEmpty() && pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.CREATE_RECOVERY_CODES),
        style = TaxiButtonStyle.Secondary,
    )
    state.recoveryCodes?.let { bundle ->
        ToastBanner(stringResource(Res.string.recovery_codes_save_warning), StatusTone.Warning)
        bundle.codes.forEach { code ->
            Text(ltrIsolate(code), style = MaterialTheme.typography.titleMedium)
        }
        Text(stringResource(Res.string.recovery_codes_expire, ltrIsolate(bundle.expiresAt)))
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
        ) {
            Checkbox(
                checked = recoveryCodesSaved,
                onCheckedChange = { recoveryCodesSaved = it },
                modifier = Modifier.testTag("recovery-codes-saved-check"),
            )
            Text(stringResource(Res.string.recovery_codes_saved_acknowledgement))
        }
        TaxiButton(
            label = stringResource(Res.string.clear_recovery_codes),
            onClick = onAcknowledgeRecoveryCodes,
            enabled = recoveryCodesSaved && pendingAction == null,
            modifier = Modifier.testTag("clear-recovery-codes"),
            style = TaxiButtonStyle.Tertiary,
        )
    }

    Text(stringResource(Res.string.change_password), style = MaterialTheme.typography.titleMedium)
    Text(stringResource(Res.string.change_password_warning))
    PasswordField(
        currentPassword,
        { currentPassword = it },
        stringResource(Res.string.current_password),
    )
    PasswordField(
        newPassword,
        { newPassword = it },
        stringResource(Res.string.new_password),
        supportingText = stringResource(Res.string.password_minimum),
    )
    TaxiButton(
        label = stringResource(Res.string.change_password),
        onClick = { onChangePassword(currentPassword, newPassword) },
        enabled = currentPassword.isNotEmpty() && newPassword.length >= 12 && pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.CHANGE_ACCOUNT_PASSWORD),
        style = TaxiButtonStyle.Secondary,
    )

    sessionToRevoke?.let { session ->
        ConfirmDialog(
            title = if (session.current) {
                stringResource(Res.string.sign_out_this_session_question)
            } else {
                stringResource(Res.string.revoke_session_question)
            },
            body = stringResource(Res.string.revoke_session_explanation),
            confirmLabel = if (session.current) {
                stringResource(Res.string.sign_out)
            } else {
                stringResource(Res.string.revoke_session)
            },
            destructive = true,
            onConfirm = {
                sessionToRevoke = null
                onRevokeSession(session.id)
            },
            onCancel = { sessionToRevoke = null },
        )
    }
}
