package org.example.taximobile.feature.ui.text

import kotlin.test.Test
import kotlin.test.assertEquals

class BidiTextTest {
    @Test
    fun machine_identifier_is_wrapped_in_ltr_isolate_controls() {
        assertEquals("\u2066TX-1234\u2069", ltrIsolate("TX-1234"))
    }
}
