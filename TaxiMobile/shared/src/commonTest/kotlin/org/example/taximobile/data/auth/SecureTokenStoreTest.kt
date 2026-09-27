package org.example.taximobile.data.auth

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class SecureTokenStoreTest {
    @Test
    fun `token envelope round trips without delimiter assumptions`() {
        val tokens = StoredTokens(
            accessToken = "access.with:punctuation/and-unicode-سلام",
            refreshToken = "refresh\u0000with-an-embedded-null",
        )

        assertEquals(tokens, decodeStoredTokens(encodeStoredTokens(tokens)))
    }

    @Test
    fun `token envelope rejects truncation and trailing data`() {
        val encoded = encodeStoredTokens(StoredTokens("access", "refresh"))

        assertNull(decodeStoredTokens(encoded.copyOf(encoded.size - 1)))
        assertNull(decodeStoredTokens(encoded + 0))
    }

    @Test
    fun `token envelope rejects unknown versions and impossible lengths`() {
        val encoded = encodeStoredTokens(StoredTokens("access", "refresh"))

        assertNull(decodeStoredTokens(encoded.copyOf().also { it[0] = 2 }))
        assertNull(decodeStoredTokens(encoded.copyOf().also { it[1] = 1 }))
    }
}
