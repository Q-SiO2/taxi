package org.example.taximobile.feature.driver.onboarding

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import org.jetbrains.compose.resources.StringResource
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

/** Present the server's recorded status; presence of a record never means approval. */
internal fun cityAuthorizationStatusResource(status: String): StringResource = when (status) {
    "ACTIVE" -> Res.string.city_authorization_active
    "SUSPENDED" -> Res.string.city_authorization_suspended
    "EXPIRED" -> Res.string.city_authorization_expired
    "REVOKED" -> Res.string.city_authorization_revoked
    else -> Res.string.city_authorization_unknown
}

/** Keep localized resources within shared while exposing the same recorded-state UI to each client. */
@Composable
fun CityAuthorizationSummary(status: String, validUntil: String?) {
    Text(stringResource(cityAuthorizationStatusResource(status)), style = MaterialTheme.typography.titleMedium)
    validUntil?.let { Text(stringResource(Res.string.city_authorization_valid_until, it)) }
    Text(stringResource(Res.string.city_authorization_eligibility_notice), style = MaterialTheme.typography.bodySmall)
}
