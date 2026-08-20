package org.example.taximobile.feature.notifications

import kotlinx.coroutines.runBlocking
import org.example.taximobile.domain.notifications.DevicePlatform
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class PushRegistrationRelayTest {
    @Test
    fun `token issued before authentication is available to a later retry`() = runBlocking {
        val relay = PushRegistrationRelay(DevicePlatform.ANDROID)
        relay.remember("  provider-token  ")
        var attempts = 0

        assertFalse(relay.retry { _, _ -> attempts++; false })
        assertTrue(relay.retry { token, platform ->
            attempts++
            token == "provider-token" && platform == DevicePlatform.ANDROID
        })
        assertEquals(2, attempts)
    }

    @Test
    fun `blank provider callback does not create registration work`() = runBlocking {
        val relay = PushRegistrationRelay(DevicePlatform.IOS)
        relay.remember("   ")

        assertFalse(relay.retry { _, _ -> true })
    }

    @Test
    fun `successful registration remains retryable for a later signed in account`() = runBlocking {
        val relay = PushRegistrationRelay(DevicePlatform.IOS)
        relay.remember("ios-token")
        val registeredTokens = mutableListOf<String>()

        repeat(2) {
            assertTrue(relay.retry { token, _ -> registeredTokens.add(token) })
        }

        assertEquals(listOf("ios-token", "ios-token"), registeredTokens)
    }
}
