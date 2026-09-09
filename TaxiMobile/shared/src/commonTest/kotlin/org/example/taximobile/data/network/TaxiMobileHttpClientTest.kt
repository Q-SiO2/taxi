package org.example.taximobile.data.network

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class TaxiMobileHttpClientTest {
    @Test
    fun closedClientIdentityAcceptsEveryShippedSurface() {
        TaxiMobileClientSurface.entries.forEach { surface ->
            val identity = TaxiMobileClientIdentity(surface, "1.2.3", "42")
            assertEquals(surface, identity.surface)
        }
    }

    @Test
    fun clientIdentityRejectsNonReleaseVersionsAndInvalidBuilds() {
        for (version in listOf("1", "1.0", "1.0.0-debug", "v1.0.0", "01.0.0")) {
            assertFailsWith<IllegalArgumentException> {
                TaxiMobileClientIdentity(
                    TaxiMobileClientSurface.ANDROID_PASSENGER,
                    version,
                    "1",
                )
            }
        }
        for (build in listOf("", "0", "-1", "2147483648")) {
            assertFailsWith<IllegalArgumentException> {
                TaxiMobileClientIdentity(
                    TaxiMobileClientSurface.IOS_DRIVER,
                    "1.0.0",
                    build,
                )
            }
        }
    }
}
