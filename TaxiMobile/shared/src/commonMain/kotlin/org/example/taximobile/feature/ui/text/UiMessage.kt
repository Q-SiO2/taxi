package org.example.taximobile.feature.ui.text

import androidx.compose.runtime.Composable
import org.jetbrains.compose.resources.StringResource
import org.jetbrains.compose.resources.stringResource

/**
 * Stable presentation message carried through coordinators without embedding a
 * language in business or network state. Arguments are presentation-only and
 * are substituted by the active Compose locale at render time.
 */
data class UiMessage(
    val resource: StringResource,
    val arguments: List<Any> = emptyList(),
)

@Composable
fun UiMessage.resolve(): String = stringResource(resource, *arguments.toTypedArray())
