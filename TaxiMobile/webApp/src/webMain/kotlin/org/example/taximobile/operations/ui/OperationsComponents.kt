package org.example.taximobile.operations.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.state.OperationsMessage

@Composable
internal fun OperationsWordmark(compact: Boolean = false) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
    ) {
        Box(
            modifier = Modifier
                .size(38.dp)
                .background(TaxiColors.Accent500, RoundedCornerShape(TaxiRadii.Md)),
            contentAlignment = Alignment.Center,
        ) {
            Text("TM", color = TaxiColors.Navy950, fontWeight = FontWeight.ExtraBold)
        }
        if (!compact) {
            Column {
                Text(
                    "TaxiMobile",
                    color = Color.White,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    "National operations",
                    color = TaxiColors.Navy200,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }
}

@Composable
internal fun StatusBadge(status: String, modifier: Modifier = Modifier) {
    val normalized = status.uppercase()
    val (background, foreground) = when (normalized) {
        "ACTIVE", "PASSED", "APPROVED", "RESOLVED" -> TaxiColors.Success100 to TaxiColors.Success600
        "PILOT", "CONFIGURING", "IN_REVIEW", "PENDING", "HIGH", "ACKNOWLEDGED", "IN_PROGRESS" -> TaxiColors.Warning100 to TaxiColors.Warning600
        "PAUSED", "FAILED", "URGENT", "OPEN", "ESCALATED" -> TaxiColors.Danger100 to TaxiColors.Danger600
        "RETIRED", "REPLACED", "REVOKED", "CLOSED" -> TaxiColors.Surface2 to TaxiColors.Ink700
        "DRAFT" -> TaxiColors.Navy100 to TaxiColors.Navy700
        else -> TaxiColors.Info100 to TaxiColors.Info600
    }
    Surface(
        modifier = modifier,
        color = background,
        shape = CircleShape,
        border = BorderStroke(1.dp, foreground.copy(alpha = 0.22f)),
    ) {
        Text(
            normalized.replace('_', ' '),
            modifier = Modifier.padding(horizontal = TaxiSpacing.Sm, vertical = TaxiSpacing.Xs),
            color = foreground,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
internal fun MessageBanner(
    message: OperationsMessage,
    error: Boolean,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val background = if (error) TaxiColors.Danger100 else TaxiColors.Success100
    val foreground = if (error) TaxiColors.Danger600 else TaxiColors.Success600
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = background,
        shape = RoundedCornerShape(TaxiRadii.Md),
        border = BorderStroke(1.dp, foreground.copy(alpha = 0.25f)),
    ) {
        Row(
            modifier = Modifier.padding(TaxiSpacing.Md),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier.size(10.dp).background(foreground, CircleShape),
            )
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
                Text(message.title, color = foreground, fontWeight = FontWeight.Bold)
                Text(message.detail, color = TaxiColors.Ink700, style = MaterialTheme.typography.bodySmall)
            }
            OutlinedButton(
                onClick = onDismiss,
                colors = ButtonDefaults.outlinedButtonColors(contentColor = foreground),
                border = BorderStroke(1.dp, foreground.copy(alpha = 0.45f)),
            ) {
                Text("Dismiss")
            }
        }
    }
}

@Composable
internal fun MetricCard(
    label: String,
    value: String,
    supportingText: String,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier.widthIn(min = 180.dp),
        color = TaxiColors.Surface0,
        shape = RoundedCornerShape(TaxiRadii.Lg),
        border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
    ) {
        Column(
            Modifier.padding(TaxiSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
        ) {
            Text(label, color = TaxiColors.Ink500, style = MaterialTheme.typography.labelMedium)
            Text(value, color = TaxiColors.Navy900, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Text(supportingText, color = TaxiColors.Ink700, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
internal fun SectionHeading(
    title: String,
    supportingText: String,
    modifier: Modifier = Modifier,
    action: (@Composable () -> Unit)? = null,
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
            Text(title, style = MaterialTheme.typography.headlineSmall, color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
            Text(supportingText, style = MaterialTheme.typography.bodyMedium, color = TaxiColors.Ink500)
        }
        action?.invoke()
    }
}

@Composable
internal fun EmptyState(
    title: String,
    detail: String,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = TaxiColors.Surface0,
        shape = RoundedCornerShape(TaxiRadii.Lg),
        border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
    ) {
        Column(
            Modifier.padding(TaxiSpacing.Xxl),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            Box(
                Modifier.size(44.dp).background(TaxiColors.Navy100, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text("—", color = TaxiColors.Navy700, fontWeight = FontWeight.Bold)
            }
            Text(title, color = TaxiColors.Navy900, style = MaterialTheme.typography.titleMedium)
            Text(detail, color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
        }
    }
}

data class ScopeOption(val id: String?, val label: String)

@Composable
internal fun ScopeMenu(
    label: String,
    selected: String,
    options: List<ScopeOption>,
    enabled: Boolean,
    onSelected: (String?) -> Unit,
    modifier: Modifier = Modifier,
) {
    var expanded by remember { mutableStateOf(false) }
    Box(modifier) {
        Surface(
            modifier = Modifier
                .widthIn(min = 150.dp, max = 230.dp)
                .clickable(enabled = enabled) { expanded = true },
            color = TaxiColors.Surface0,
            shape = RoundedCornerShape(TaxiRadii.Md),
            border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
        ) {
            Column(Modifier.padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Xs)) {
                Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = TaxiColors.Ink500)
                Text(
                    "$selected  ▾",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TaxiColors.Navy900,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option.label, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                    onClick = {
                        expanded = false
                        onSelected(option.id)
                    },
                )
            }
        }
    }
}

@Composable
internal fun DataCard(
    modifier: Modifier = Modifier,
    tableMinWidth: Dp? = null,
    content: @Composable () -> Unit,
) {
    if (tableMinWidth != null) {
        BoxWithConstraints(modifier.fillMaxWidth()) {
            val cardWidth = if (maxWidth < tableMinWidth) tableMinWidth else maxWidth
            Box(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
                Surface(
                    modifier = Modifier.width(cardWidth),
                    color = TaxiColors.Surface0,
                    shape = RoundedCornerShape(TaxiRadii.Lg),
                    border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
                    content = content,
                )
            }
        }
    } else {
        Surface(
            modifier = modifier.fillMaxWidth(),
            color = TaxiColors.Surface0,
            shape = RoundedCornerShape(TaxiRadii.Lg),
            border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
            content = content,
        )
    }
}

@Composable
internal fun KeyValue(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = TaxiColors.Ink500)
        Text(value, style = MaterialTheme.typography.bodyMedium, color = TaxiColors.Ink900)
    }
}

@Composable
internal fun PageLimitNote(shown: Int, total: Int) {
    if (total <= shown) return
    Spacer(Modifier.height(TaxiSpacing.Sm))
    Text(
        "Showing the first $shown of $total scoped records. API pagination remains authoritative.",
        color = TaxiColors.Warning600,
        style = MaterialTheme.typography.bodySmall,
        modifier = Modifier
            .fillMaxWidth()
            .background(TaxiColors.Warning100, RoundedCornerShape(TaxiRadii.Sm))
            .border(1.dp, TaxiColors.Warning600.copy(alpha = 0.2f), RoundedCornerShape(TaxiRadii.Sm))
            .padding(TaxiSpacing.Sm),
    )
}

internal fun shortId(value: String?): String = when {
    value == null -> "—"
    value.length <= 12 -> value
    else -> "${value.take(8)}…${value.takeLast(4)}"
}

internal fun compactTimestamp(value: String?): String {
    if (value == null) return "—"
    val withoutZulu = value.removeSuffix("Z")
    val positiveOffset = withoutZulu.indexOf('+', startIndex = 10)
    val negativeOffset = withoutZulu.indexOf('-', startIndex = 11)
    val offsetIndex = listOf(positiveOffset, negativeOffset)
        .filter { it >= 0 }
        .minOrNull()
    val dateTime = if (offsetIndex == null) withoutZulu else withoutZulu.substring(0, offsetIndex)
    val core = dateTime.substringBefore('.').replace('T', ' ')
    val isUtc = value.endsWith('Z') || value.contains("+00:00")
    val offset = offsetIndex?.let { withoutZulu.substring(it) }
    return when {
        isUtc -> "$core UTC"
        offset != null -> "$core $offset"
        else -> core
    }
}
