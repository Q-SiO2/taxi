package org.example.taximobile.data.auth

import android.content.Context
import android.content.SharedPreferences
import java.util.WeakHashMap
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/**
 * One encrypted token-pair envelope; AES-GCM keys remain in Android Keystore.
 * Only an entirely absent record is signed out. Facility/corruption failures
 * never erase an existing session. Legacy pairs migrate after both decrypt and
 * a checked write commits. Disk operations run off the UI thread, serialized.
 */
class AndroidSecureTokenStore internal constructor(
    private val preferencesProvider: () -> SharedPreferences,
    private val cipher: AndroidSessionCipher,
) : SecureTokenStore {
    constructor(context: Context) : this(
        { context.getSharedPreferences("taximobile.secure_session", Context.MODE_PRIVATE) },
        AndroidKeystoreSessionCipher(),
    )

    internal constructor(preferences: SharedPreferences, cipher: AndroidSessionCipher) :
        this({ preferences }, cipher)

    // Even preference-facility initialization belongs inside error translation.
    private val preferences by lazy { preferencesProvider() }

    override suspend fun tokens(): StoredTokens? = protectedOperation("read") { preferences, lifetime ->
        check(!lifetime.persistenceUncertain)
        val snapshot = preferences.all
        val envelope = snapshot.stringRecord(SESSION)
        if (envelope != null) {
            return@protectedOperation decodeStoredTokens(cipher.decrypt(envelope))
                ?: error("Invalid protected session envelope")
        }
        val access = snapshot.stringRecord(LEGACY_ACCESS)
        val refresh = snapshot.stringRecord(LEGACY_REFRESH)
        if (access == null && refresh == null) return@protectedOperation null
        check(access != null && refresh != null)
        val tokens = StoredTokens(
            cipher.decrypt(access).decodeToString(throwOnInvalidSequence = true),
            cipher.decrypt(refresh).decodeToString(throwOnInvalidSequence = true),
        )
        write(tokens, preferences, lifetime)
        tokens
    }

    override suspend fun save(accessToken: String, refreshToken: String): Unit =
        protectedOperation("save") { preferences, lifetime ->
            write(StoredTokens(accessToken, refreshToken), preferences, lifetime)
        }

    override suspend fun clear(): Unit = protectedOperation("clear") { preferences, lifetime ->
        commit(preferences.edit().remove(SESSION).remove(LEGACY_ACCESS).remove(LEGACY_REFRESH), lifetime)
    }

    private fun write(tokens: StoredTokens, preferences: SharedPreferences, lifetime: PersistenceLifetime) {
        val encrypted = cipher.encrypt(encodeStoredTokens(tokens))
        commit(preferences.edit().putString(SESSION, encrypted)
            .remove(LEGACY_ACCESS).remove(LEGACY_REFRESH), lifetime)
    }

    private fun commit(editor: SharedPreferences.Editor, lifetime: PersistenceLifetime) {
        lifetime.persistenceUncertain = true
        check(editor.commit())
        lifetime.persistenceUncertain = false
    }

    private suspend fun <T> protectedOperation(
        operation: String,
        block: (SharedPreferences, PersistenceLifetime) -> T,
    ): T = withContext(Dispatchers.IO) {
        try {
            val facility = preferences
            val lifetime = persistenceLifetime(facility)
            lifetime.operations.withLock { block(facility, lifetime) }
        } catch (error: CancellationException) {
            throw error
        } catch (_: Exception) {
            // Platform causes may contain alias/ciphertext/credential data.
            throw SecureTokenStorageException("Protected session $operation failed")
        }
    }

    private class PersistenceLifetime {
        val operations = Mutex()
        // commit() can mutate Android's process-cached map even on failure.
        // Activity/store recreation must not trust that unpersisted memory.
        var persistenceUncertain = false
    }

    private fun persistenceLifetime(facility: SharedPreferences): PersistenceLifetime =
        synchronized(lifetimes) {
            lifetimes.getOrPut(facility) { PersistenceLifetime() }
        }

    private fun Map<String, *>.stringRecord(key: String): String? {
        if (!containsKey(key)) return null
        val record = get(key)
        check(record is String && record.isNotEmpty())
        return record
    }

    internal companion object {
        const val SESSION = "session_envelope_v1"
        const val LEGACY_ACCESS = "access_token"
        const val LEGACY_REFRESH = "refresh_token"

        // Android caches this facility per package/file. Weak keys release an
        // unused facility without retaining credentials or a Context here.
        private val lifetimes = WeakHashMap<SharedPreferences, PersistenceLifetime>()
    }
}
