package org.example.taximobile.core.network

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue
import org.example.taximobile.data.network.newIdempotencyKey

class ApiConfigurationTest {
    @Test
    fun creates_v1_endpoints_without_double_slashes() {
        val configuration = ApiConfiguration("https://api.example.test")

        assertEquals("https://api.example.test/api/v1/meta", configuration.endpoint("/meta"))
        assertEquals("wss://api.example.test/api/v1/events", configuration.websocketEndpoint("events"))
    }

    @Test
    fun rejects_ambiguous_base_urls() {
        assertFailsWith<IllegalArgumentException> { ApiConfiguration("api.example.test") }
        assertFailsWith<IllegalArgumentException> { ApiConfiguration("https://api.example.test/") }
    }
}

class IdempotencyKeyTest {
    @Test
    fun creates_a_backend_accepted_command_key() {
        val key = newIdempotencyKey()

        assertEquals(32, key.length)
        assertTrue(key.all { it in '0'..'9' || it in 'a'..'f' })
    }
}
