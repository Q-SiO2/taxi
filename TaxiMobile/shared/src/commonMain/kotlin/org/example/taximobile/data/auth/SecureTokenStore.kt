package org.example.taximobile.data.auth

/**
 * Platform implementations must use the operating system's protected
 * credential facility. Refresh tokens must never be placed in normal app
 * preferences, UI state, analytics, or logs.
 */
interface SecureTokenStore {
    suspend fun tokens(): StoredTokens?
    suspend fun save(accessToken: String, refreshToken: String)
    suspend fun clear()
}

/** A protected credential facility failed without exposing credential data. */
class SecureTokenStorageException(message: String) : Exception(message)

data class StoredTokens(
    val accessToken: String,
    val refreshToken: String,
)

/**
 * Versioned, length-delimited token pair used by stores that can atomically
 * replace one protected value. It deliberately avoids delimiter assumptions
 * about current or future token formats.
 */
internal fun encodeStoredTokens(tokens: StoredTokens): ByteArray {
    val access = tokens.accessToken.encodeToByteArray()
    val refresh = tokens.refreshToken.encodeToByteArray()
    require(access.isNotEmpty() && refresh.isNotEmpty()) { "Session tokens must not be empty" }
    require(access.size <= MAX_TOKEN_BYTES && refresh.size <= MAX_TOKEN_BYTES) {
        "Session token exceeds the protected-storage limit"
    }

    return ByteArray(TOKEN_ENVELOPE_HEADER_BYTES + access.size + refresh.size).also { encoded ->
        encoded[0] = TOKEN_ENVELOPE_VERSION
        encoded.writeInt(1, access.size)
        encoded.writeInt(5, refresh.size)
        access.copyInto(encoded, TOKEN_ENVELOPE_HEADER_BYTES)
        refresh.copyInto(encoded, TOKEN_ENVELOPE_HEADER_BYTES + access.size)
    }
}

internal fun decodeStoredTokens(encoded: ByteArray): StoredTokens? {
    if (encoded.size < TOKEN_ENVELOPE_HEADER_BYTES || encoded[0] != TOKEN_ENVELOPE_VERSION) return null
    val accessSize = encoded.readInt(1)
    val refreshSize = encoded.readInt(5)
    if (accessSize !in 1..MAX_TOKEN_BYTES || refreshSize !in 1..MAX_TOKEN_BYTES) return null
    if (encoded.size != TOKEN_ENVELOPE_HEADER_BYTES + accessSize + refreshSize) return null

    return runCatching {
        val access = encoded.decodeToString(
            startIndex = TOKEN_ENVELOPE_HEADER_BYTES,
            endIndex = TOKEN_ENVELOPE_HEADER_BYTES + accessSize,
            throwOnInvalidSequence = true,
        )
        val refresh = encoded.decodeToString(
            startIndex = TOKEN_ENVELOPE_HEADER_BYTES + accessSize,
            endIndex = encoded.size,
            throwOnInvalidSequence = true,
        )
        StoredTokens(accessToken = access, refreshToken = refresh)
    }.getOrNull()
}

private fun ByteArray.writeInt(offset: Int, value: Int) {
    this[offset] = (value ushr 24).toByte()
    this[offset + 1] = (value ushr 16).toByte()
    this[offset + 2] = (value ushr 8).toByte()
    this[offset + 3] = value.toByte()
}

private fun ByteArray.readInt(offset: Int): Int =
    ((this[offset].toInt() and 0xff) shl 24) or
        ((this[offset + 1].toInt() and 0xff) shl 16) or
        ((this[offset + 2].toInt() and 0xff) shl 8) or
        (this[offset + 3].toInt() and 0xff)

private const val TOKEN_ENVELOPE_VERSION: Byte = 1
private const val TOKEN_ENVELOPE_HEADER_BYTES = 9
private const val MAX_TOKEN_BYTES = 64 * 1024
