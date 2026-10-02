package org.example.taximobile.data.auth

import android.content.SharedPreferences
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

/** Actual adapter control flow with synthetic prefs/cipher; not OS acceptance. */
class AndroidSecureTokenStoreTest {
    @Test fun preferenceFacilityInitializationFailureIsActionableAndRetryable() = runBlocking {
        var unavailable = true
        val prefs = TestPreferences()
        val store = AndroidSecureTokenStore({
            check(!unavailable) { "private context detail" }
            prefs
        }, TestCipher())
        val failure = assertFailsWith<SecureTokenStorageException> { store.tokens() }
        assertSanitizedFailure(failure, "read")
        unavailable = false
        assertNull(store.tokens())
    }

    @Test fun absentSessionDoesNotWriteOrGenerateCiphertext() = runBlocking {
        val prefs = TestPreferences()
        val cipher = TestCipher()
        assertNull(AndroidSecureTokenStore(prefs, cipher).tokens())
        assertEquals(0, prefs.commits)
        assertTrue(cipher.records.isEmpty())
    }

    @Test fun roundTripUsesOneEncryptedEnvelopeAndPreservesOtherPreferences() = runBlocking {
        val prefs = TestPreferences(mutableMapOf("unrelated" to "setting"))
        val store = AndroidSecureTokenStore(prefs, TestCipher())
        store.save("synthetic-access", "synthetic-refresh")
        assertEquals(StoredTokens("synthetic-access", "synthetic-refresh"), store.tokens())
        assertEquals(setOf("unrelated", AndroidSecureTokenStore.SESSION), prefs.values.keys)
        assertEquals("cipher-0", prefs.values[AndroidSecureTokenStore.SESSION])
        assertEquals(1, prefs.commits)
    }

    @Test fun completeLegacyPairMigratesOnlyAfterSuccessfulCommit() = runBlocking {
        val cipher = TestCipher()
        val prefs = TestPreferences(mutableMapOf(
            AndroidSecureTokenStore.LEGACY_ACCESS to cipher.encrypt("old-access".encodeToByteArray()),
            AndroidSecureTokenStore.LEGACY_REFRESH to cipher.encrypt("old-refresh".encodeToByteArray()),
        ))
        assertEquals(StoredTokens("old-access", "old-refresh"), AndroidSecureTokenStore(prefs, cipher).tokens())
        assertEquals(setOf(AndroidSecureTokenStore.SESSION), prefs.values.keys)
        assertEquals(1, prefs.commits)
    }

    @Test fun incompleteLegacyPairIsNotSilentlyCleared() = runBlocking {
        for (key in listOf(AndroidSecureTokenStore.LEGACY_ACCESS, AndroidSecureTokenStore.LEGACY_REFRESH)) {
            val prefs = TestPreferences(mutableMapOf(key to "incomplete"))
            assertFailsWith<SecureTokenStorageException> { AndroidSecureTokenStore(prefs, TestCipher()).tokens() }
            assertEquals<Map<String, Any?>>(mapOf(key to "incomplete"), prefs.values)
            assertEquals(0, prefs.commits)
        }
    }

    @Test fun decryptionFailurePreservesNewAndLegacyRecords() = runBlocking {
        for (values in listOf(
            mutableMapOf<String, Any?>(AndroidSecureTokenStore.SESSION to "unreadable"),
            mutableMapOf<String, Any?>(AndroidSecureTokenStore.LEGACY_ACCESS to "unreadable",
                AndroidSecureTokenStore.LEGACY_REFRESH to "unreadable"),
        )) {
            val prefs = TestPreferences(values.toMutableMap())
            val error = assertFailsWith<SecureTokenStorageException> {
                AndroidSecureTokenStore(prefs, TestCipher()).tokens()
            }
            assertSanitizedFailure(error, "read")
            assertEquals(values, prefs.values)
            assertEquals(0, prefs.commits)
        }
    }

    @Test fun malformedEnvelopeRemainsExplicitAndPreserved() = runBlocking {
        val cipher = TestCipher()
        val record = cipher.encrypt(byteArrayOf(0, 1, 2))
        val prefs = TestPreferences(mutableMapOf(AndroidSecureTokenStore.SESSION to record))
        assertFailsWith<SecureTokenStorageException> { AndroidSecureTokenStore(prefs, cipher).tokens() }
        assertEquals(record, prefs.values[AndroidSecureTokenStore.SESSION])
        assertEquals(0, prefs.commits)
    }

    @Test fun mistypedEmptyOrNullRecordIsNotAbsence() = runBlocking {
        for (record in listOf(42, "", null)) {
            val prefs = TestPreferences(mutableMapOf(AndroidSecureTokenStore.SESSION to record))
            assertFailsWith<SecureTokenStorageException> { AndroidSecureTokenStore(prefs, TestCipher()).tokens() }
            assertTrue(prefs.values.containsKey(AndroidSecureTokenStore.SESSION))
            assertEquals(0, prefs.commits)
        }
    }

    @Test fun preferenceReadFailureIsSanitizedAndDoesNotErase() = runBlocking {
        val prefs = TestPreferences(mutableMapOf(AndroidSecureTokenStore.SESSION to "preserved"))
        prefs.failRead = true
        val error = assertFailsWith<SecureTokenStorageException> {
            AndroidSecureTokenStore(prefs, TestCipher()).tokens()
        }
        assertSanitizedFailure(error, "read")
        assertEquals("preserved", prefs.values[AndroidSecureTokenStore.SESSION])
        assertEquals(0, prefs.commits)
    }

    @Test fun encryptionFailureDoesNotEditPreviousSession() = runBlocking {
        val prefs = TestPreferences(mutableMapOf(AndroidSecureTokenStore.SESSION to "preserved"))
        val cipher = TestCipher().also { it.failEncrypt = true }
        val error = assertFailsWith<SecureTokenStorageException> {
            AndroidSecureTokenStore(prefs, cipher).save("new-access", "new-refresh")
        }
        assertSanitizedFailure(error, "save")
        assertEquals("preserved", prefs.values[AndroidSecureTokenStore.SESSION])
        assertEquals(0, prefs.commits)
    }

    @Test fun failedCommitCannotRestoreUnpersistedMemoryAndExplicitSaveRecovers() = runBlocking {
        val prefs = TestPreferences().also { it.failCommit = true }
        val store = AndroidSecureTokenStore(prefs, TestCipher())
        assertFailsWith<SecureTokenStorageException> { store.save("lost-access", "lost-refresh") }
        assertNotNull(prefs.values[AndroidSecureTokenStore.SESSION]) // Android-like memory mutation.
        assertFailsWith<SecureTokenStorageException> { store.tokens() }
        prefs.failCommit = false
        store.save("durable-access", "durable-refresh")
        assertEquals(StoredTokens("durable-access", "durable-refresh"), store.tokens())
    }

    @Test fun replacementStoreCannotTrustMemoryAfterAFailedWrite() = runBlocking {
        val prefs = TestPreferences().also { it.failCommit = true }
        val cipher = TestCipher()
        val original = AndroidSecureTokenStore(prefs, cipher)
        assertFailsWith<SecureTokenStorageException> { original.save("lost-access", "lost-refresh") }
        val replacement = AndroidSecureTokenStore(prefs, cipher)
        assertFailsWith<SecureTokenStorageException> { replacement.tokens() }
        prefs.failCommit = false
        replacement.save("durable-access", "durable-refresh")
        assertEquals(StoredTokens("durable-access", "durable-refresh"), original.tokens())
        replacement.clear()
        assertNull(original.tokens())
    }

    @Test fun uncertainFacilityDoesNotBlockAnIndependentFacility(): Unit = runBlocking {
        val brokenPrefs = TestPreferences().also { it.failCommit = true }
        val broken = AndroidSecureTokenStore(brokenPrefs, TestCipher())
        assertFailsWith<SecureTokenStorageException> { broken.save("lost-access", "lost-refresh") }
        val independent = AndroidSecureTokenStore(TestPreferences(), TestCipher())
        independent.save("access", "refresh")
        assertEquals(StoredTokens("access", "refresh"), independent.tokens())
        assertFailsWith<SecureTokenStorageException> { broken.tokens() }
    }

    @Test fun throwingCommitAlsoLeavesPersistenceUncertain() = runBlocking {
        val prefs = TestPreferences().also { it.throwCommit = true }
        val store = AndroidSecureTokenStore(prefs, TestCipher())
        val error = assertFailsWith<SecureTokenStorageException> { store.save("new-access", "new-refresh") }
        assertSanitizedFailure(error, "save")
        assertFailsWith<SecureTokenStorageException> { store.tokens() }
        prefs.throwCommit = false
        store.clear()
        assertNull(store.tokens())
    }

    @Test fun legacyMigrationFailureDoesNotExposeAnUncommittedPair() = runBlocking {
        val cipher = TestCipher()
        val prefs = TestPreferences(mutableMapOf(
            AndroidSecureTokenStore.LEGACY_ACCESS to cipher.encrypt("old-access".encodeToByteArray()),
            AndroidSecureTokenStore.LEGACY_REFRESH to cipher.encrypt("old-refresh".encodeToByteArray()),
        )).also { it.failCommit = true }
        val store = AndroidSecureTokenStore(prefs, cipher)
        assertFailsWith<SecureTokenStorageException> { store.tokens() }
        assertFailsWith<SecureTokenStorageException> { store.tokens() }
        assertEquals(1, prefs.commits)
    }

    @Test fun explicitClearRequiresPersistenceAndKeepsUnrelatedValues() = runBlocking {
        val prefs = TestPreferences(mutableMapOf("unrelated" to "setting"))
        val store = AndroidSecureTokenStore(prefs, TestCipher())
        store.save("access", "refresh")
        prefs.failCommit = true
        val error = assertFailsWith<SecureTokenStorageException> { store.clear() }
        assertEquals("Protected session clear failed", error.message)
        assertFailsWith<SecureTokenStorageException> { store.tokens() }
        prefs.failCommit = false
        store.clear()
        assertNull(store.tokens())
        assertEquals<Map<String, Any?>>(mapOf("unrelated" to "setting"), prefs.values)
    }

    @Test fun cancellationIsNotAStorageFailure() = runBlocking {
        val cipher = TestCipher().also { it.cancelEncrypt = true }
        val prefs = TestPreferences()
        assertFailsWith<CancellationException> { AndroidSecureTokenStore(prefs, cipher).save("access", "refresh") }
        assertEquals(0, prefs.commits)
    }

    @Test fun validEnvelopeIsAuthoritativeEvenWhenLegacyRecordsAreCorrupt() = runBlocking {
        val cipher = TestCipher()
        val record = cipher.encrypt(encodeStoredTokens(StoredTokens("access", "refresh")))
        val prefs = TestPreferences(mutableMapOf(
            AndroidSecureTokenStore.SESSION to record,
            AndroidSecureTokenStore.LEGACY_ACCESS to "unreadable",
            AndroidSecureTokenStore.LEGACY_REFRESH to null,
        ))
        assertEquals(StoredTokens("access", "refresh"), AndroidSecureTokenStore(prefs, cipher).tokens())
        assertEquals(0, prefs.commits)
    }

    @Test fun transientReadFailureDoesNotRequireDeletingTheStoredSession() = runBlocking {
        val prefs = TestPreferences()
        val store = AndroidSecureTokenStore(prefs, TestCipher())
        store.save("access", "refresh")
        val durableRecord = prefs.values.toMap()
        prefs.failRead = true
        assertSanitizedFailure(assertFailsWith<SecureTokenStorageException> { store.tokens() }, "read")
        assertEquals(durableRecord, prefs.values)
        prefs.failRead = false
        assertEquals(StoredTokens("access", "refresh"), store.tokens())
        assertEquals(1, prefs.commits)
    }

    @Test fun invalidLegacyPlaintextCannotBeMigratedOrSilentlyCleared() = runBlocking {
        val invalidValues = listOf(byteArrayOf(), byteArrayOf(0xc3.toByte(), 0x28), ByteArray(65_537) { 65 })
        for (invalid in invalidValues) {
            for (invalidAccess in listOf(true, false)) {
                val cipher = TestCipher()
                val valid = "valid-token".encodeToByteArray()
                val prefs = TestPreferences(mutableMapOf(
                    AndroidSecureTokenStore.LEGACY_ACCESS to cipher.encrypt(if (invalidAccess) invalid else valid),
                    AndroidSecureTokenStore.LEGACY_REFRESH to cipher.encrypt(if (invalidAccess) valid else invalid),
                ))
                val previous = prefs.values.toMap()
                assertSanitizedFailure(assertFailsWith<SecureTokenStorageException> {
                    AndroidSecureTokenStore(prefs, cipher).tokens()
                }, "read")
                assertEquals(previous, prefs.values)
                assertEquals(0, prefs.commits)
            }
        }
    }

    @Test fun invalidReplacementDoesNotEditTheExistingEnvelope() = runBlocking {
        val prefs = TestPreferences()
        val store = AndroidSecureTokenStore(prefs, TestCipher())
        store.save("access", "refresh")
        val previous = prefs.values.toMap()
        for ((access, refresh) in listOf("" to "refresh", "access" to "", "a".repeat(65_537) to "refresh")) {
            assertSanitizedFailure(assertFailsWith<SecureTokenStorageException> {
                store.save(access, refresh)
            }, "save")
            assertEquals(previous, prefs.values)
            assertEquals(StoredTokens("access", "refresh"), store.tokens())
        }
        assertEquals(1, prefs.commits)
    }

    @Test fun readAcrossStoresWaitsForTheCompleteReplacementRatherThanAPartialPair() = runBlocking {
        val entered = CountDownLatch(1)
        val finish = CountDownLatch(1)
        val cipher = TestCipher().also { it.beforeEncrypt = {
            entered.countDown()
            check(finish.await(10, TimeUnit.SECONDS))
        } }
        val prefs = TestPreferences()
        val store = AndroidSecureTokenStore(prefs, cipher)
        val replacement = AndroidSecureTokenStore(prefs, cipher)
        val saving = launch { store.save("access", "refresh") }
        try {
            // Start the saver without blocking the runBlocking event loop.
            kotlinx.coroutines.yield()
            assertTrue(entered.await(10, TimeUnit.SECONDS))
            val reading = async(start = CoroutineStart.UNDISPATCHED) { replacement.tokens() }
            assertFalse(reading.isCompleted)
            finish.countDown()
            saving.join()
            assertEquals(StoredTokens("access", "refresh"), reading.await())
        } finally { finish.countDown() }
    }
}

/** Coroutine stack recovery can wrap a safe exception in another safe copy. */
private fun assertSanitizedFailure(error: SecureTokenStorageException, operation: String) {
    val visited = mutableSetOf<Throwable>()
    var current: Throwable? = error
    while (current != null) {
        val failure = current
        assertTrue(visited.add(failure), "Protected-storage exception causes must not cycle")
        assertIs<SecureTokenStorageException>(failure)
        assertEquals("Protected session $operation failed", failure.message)
        assertTrue(failure.suppressed.isEmpty(), "Platform exceptions must not escape as suppressed causes")
        current = failure.cause
    }
}

private class TestCipher : AndroidSessionCipher {
    val records = mutableMapOf<String, ByteArray>()
    var failEncrypt = false
    var cancelEncrypt = false
    var beforeEncrypt: (() -> Unit)? = null
    override fun encrypt(plaintext: ByteArray): String {
        beforeEncrypt?.invoke()
        if (cancelEncrypt) throw CancellationException("synthetic cancellation")
        check(!failEncrypt) { "private platform detail" }
        val key = "cipher-${records.size}"
        records[key] = plaintext.copyOf()
        return key
    }
    override fun decrypt(record: String): ByteArray = records[record]?.copyOf()
        ?: error("private ciphertext detail")
}

/** Deliberately models memory mutation even after a false commit result. */
private class TestPreferences(val values: MutableMap<String, Any?> = mutableMapOf()) : SharedPreferences {
    var commits = 0
    var failRead = false
    var failCommit = false
    var throwCommit = false
    override fun getAll(): MutableMap<String, *> {
        check(!failRead) { "private preference detail" }
        return values.toMutableMap()
    }
    override fun edit(): SharedPreferences.Editor = object : SharedPreferences.Editor {
        private val puts = mutableMapOf<String, Any?>()
        private val removes = mutableSetOf<String>()
        override fun putString(key: String?, value: String?): SharedPreferences.Editor = apply { puts[requireNotNull(key)] = value }
        override fun remove(key: String?): SharedPreferences.Editor = apply { removes += requireNotNull(key) }
        override fun commit(): Boolean {
            commits++
            removes.forEach(values::remove)
            values.putAll(puts)
            check(!throwCommit) { "private disk detail" }
            return !failCommit
        }
        override fun apply(): Unit = error("Async persistence must not be used")
        override fun clear(): SharedPreferences.Editor = error("Do not erase unrelated preferences")
        override fun putStringSet(key: String?, value: MutableSet<String>?): SharedPreferences.Editor = error("Unused")
        override fun putInt(key: String?, value: Int): SharedPreferences.Editor = error("Unused")
        override fun putLong(key: String?, value: Long): SharedPreferences.Editor = error("Unused")
        override fun putFloat(key: String?, value: Float): SharedPreferences.Editor = error("Unused")
        override fun putBoolean(key: String?, value: Boolean): SharedPreferences.Editor = error("Unused")
    }
    override fun contains(key: String?): Boolean = values.containsKey(key)
    override fun getString(key: String?, value: String?): String? = error("Read one atomic snapshot instead")
    override fun getStringSet(key: String?, value: MutableSet<String>?): MutableSet<String>? = error("Unused")
    override fun getInt(key: String?, value: Int): Int = error("Unused")
    override fun getLong(key: String?, value: Long): Long = error("Unused")
    override fun getFloat(key: String?, value: Float): Float = error("Unused")
    override fun getBoolean(key: String?, value: Boolean): Boolean = error("Unused")
    override fun registerOnSharedPreferenceChangeListener(listener: SharedPreferences.OnSharedPreferenceChangeListener?): Unit = error("Unused")
    override fun unregisterOnSharedPreferenceChangeListener(listener: SharedPreferences.OnSharedPreferenceChangeListener?): Unit = error("Unused")
}
