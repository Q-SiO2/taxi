package org.example.taximobile.operations.ui

import kotlin.test.Test
import kotlin.test.assertEquals

class OperationsComponentsTest {
    @Test
    fun compactTimestampPreservesSecondsAndMarksUtc() {
        assertEquals("2026-08-24 13:14:15 UTC", compactTimestamp("2026-08-24T13:14:15.987654Z"))
        assertEquals("2026-08-24 13:14:15 UTC", compactTimestamp("2026-08-24T13:14:15+00:00"))
    }

    @Test
    fun compactTimestampHandlesMissingAndOffsetValues() {
        assertEquals("—", compactTimestamp(null))
        assertEquals("2026-08-24 13:14:15 +01:00", compactTimestamp("2026-08-24T13:14:15+01:00"))
        assertEquals("2026-08-24 13:14:15 -01:00", compactTimestamp("2026-08-24T13:14:15-01:00"))
    }
}
