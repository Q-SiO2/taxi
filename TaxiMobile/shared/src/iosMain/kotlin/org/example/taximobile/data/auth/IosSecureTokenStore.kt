package org.example.taximobile.data.auth

import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.UByteVar
import kotlinx.cinterop.addressOf
import kotlinx.cinterop.alloc
import kotlinx.cinterop.cValue
import kotlinx.cinterop.memScoped
import kotlinx.cinterop.ptr
import kotlinx.cinterop.reinterpret
import kotlinx.cinterop.usePinned
import kotlinx.cinterop.value
import platform.CoreFoundation.CFDataCreate
import platform.CoreFoundation.CFDataGetBytes
import platform.CoreFoundation.CFDataGetLength
import platform.CoreFoundation.CFDataGetTypeID
import platform.CoreFoundation.CFDataRef
import platform.CoreFoundation.CFDictionaryCreateMutable
import platform.CoreFoundation.CFDictionarySetValue
import platform.CoreFoundation.CFGetTypeID
import platform.CoreFoundation.CFMutableDictionaryRef
import platform.CoreFoundation.CFRange
import platform.CoreFoundation.CFRelease
import platform.CoreFoundation.CFStringCreateWithCString
import platform.CoreFoundation.CFStringRef
import platform.CoreFoundation.CFTypeRefVar
import platform.CoreFoundation.kCFBooleanTrue
import platform.CoreFoundation.kCFStringEncodingUTF8
import platform.CoreFoundation.kCFTypeDictionaryKeyCallBacks
import platform.CoreFoundation.kCFTypeDictionaryValueCallBacks
import platform.Security.SecItemAdd
import platform.Security.SecItemCopyMatching
import platform.Security.SecItemDelete
import platform.Security.SecItemUpdate
import platform.Security.errSecDuplicateItem
import platform.Security.errSecItemNotFound
import platform.Security.errSecSuccess
import platform.Security.kSecAttrAccessible
import platform.Security.kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
import platform.Security.kSecAttrAccount
import platform.Security.kSecAttrService
import platform.Security.kSecClass
import platform.Security.kSecClassGenericPassword
import platform.Security.kSecMatchLimit
import platform.Security.kSecMatchLimitOne
import platform.Security.kSecReturnData
import platform.Security.kSecValueData

/** Uses one atomic iOS Keychain item; token values never enter user defaults or logs. */
@OptIn(ExperimentalForeignApi::class)
class IosSecureTokenStore : SecureTokenStore {
    override suspend fun tokens(): StoredTokens? {
        val encoded = read(SESSION_ACCOUNT) ?: return null
        return decodeStoredTokens(encoded) ?: run {
            delete(SESSION_ACCOUNT)
            null
        }
    }

    override suspend fun save(accessToken: String, refreshToken: String) {
        // Pre-release builds used two separate entries and could expose a
        // partial pair. Remove them before installing the atomic v1 record.
        delete(LEGACY_ACCESS_ACCOUNT)
        delete(LEGACY_REFRESH_ACCOUNT)
        write(
            SESSION_ACCOUNT,
            encodeStoredTokens(StoredTokens(accessToken = accessToken, refreshToken = refreshToken)),
        )
    }

    override suspend fun clear() {
        var firstFailure: SecureTokenStorageException? = null
        for (account in listOf(SESSION_ACCOUNT, LEGACY_ACCESS_ACCOUNT, LEGACY_REFRESH_ACCOUNT)) {
            try {
                delete(account)
            } catch (error: SecureTokenStorageException) {
                if (firstFailure == null) firstFailure = error
            }
        }
        firstFailure?.let { throw it }
    }

    private fun read(account: String): ByteArray? = memScoped {
        val result = alloc<CFTypeRefVar>()
        result.value = null
        val status = withQuery(account) { query ->
            CFDictionarySetValue(query, kSecReturnData, kCFBooleanTrue)
            CFDictionarySetValue(query, kSecMatchLimit, kSecMatchLimitOne)
            SecItemCopyMatching(query, result.ptr)
        }
        when (status) {
            errSecSuccess -> {
                val item = result.value
                    ?: throw SecureTokenStorageException("Keychain returned no session data")
                try {
                    if (CFGetTypeID(item) != CFDataGetTypeID()) {
                        throw SecureTokenStorageException("Keychain returned an unexpected session value")
                    }
                    val data: CFDataRef = item.reinterpret()
                    data.toByteArray()
                } finally {
                    CFRelease(item)
                }
            }
            errSecItemNotFound -> null
            else -> throw keychainFailure("read", status)
        }
    }

    private fun write(account: String, value: ByteArray) {
        val data = value.toCFData()
        try {
            val updateStatus = withQuery(account) { query ->
                withDictionary(
                    populate = { attributes -> CFDictionarySetValue(attributes, kSecValueData, data) },
                    block = { attributes -> SecItemUpdate(query, attributes) },
                )
            }
            if (updateStatus == errSecSuccess) return
            if (updateStatus != errSecItemNotFound) throw keychainFailure("update", updateStatus)

            val addStatus = withQuery(account) { query ->
                CFDictionarySetValue(query, kSecValueData, data)
                CFDictionarySetValue(
                    query,
                    kSecAttrAccessible,
                    kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
                )
                SecItemAdd(query, null)
            }
            when (addStatus) {
                errSecSuccess -> Unit
                errSecDuplicateItem -> {
                    val retryStatus = withQuery(account) { query ->
                        withDictionary(
                            populate = { attributes -> CFDictionarySetValue(attributes, kSecValueData, data) },
                            block = { attributes -> SecItemUpdate(query, attributes) },
                        )
                    }
                    if (retryStatus != errSecSuccess) throw keychainFailure("update", retryStatus)
                }
                else -> throw keychainFailure("add", addStatus)
            }
        } finally {
            CFRelease(data)
        }
    }

    private fun delete(account: String) {
        val status = withQuery(account) { SecItemDelete(it) }
        if (status != errSecSuccess && status != errSecItemNotFound) {
            throw keychainFailure("delete", status)
        }
    }

    private fun <T> withQuery(
        account: String,
        block: (CFMutableDictionaryRef) -> T,
    ): T {
        val service = SERVICE.toCFString()
        val accountValue = account.toCFString()
        return try {
            withDictionary(
                populate = { query ->
                    CFDictionarySetValue(query, kSecClass, kSecClassGenericPassword)
                    CFDictionarySetValue(query, kSecAttrService, service)
                    CFDictionarySetValue(query, kSecAttrAccount, accountValue)
                },
                block = block,
            )
        } finally {
            CFRelease(accountValue)
            CFRelease(service)
        }
    }

    private fun <T> withDictionary(
        populate: (CFMutableDictionaryRef) -> Unit,
        block: (CFMutableDictionaryRef) -> T,
    ): T {
        val dictionary = CFDictionaryCreateMutable(
            null,
            0,
            kCFTypeDictionaryKeyCallBacks.ptr,
            kCFTypeDictionaryValueCallBacks.ptr,
        ) ?: throw SecureTokenStorageException("Unable to allocate a Keychain request")
        return try {
            populate(dictionary)
            block(dictionary)
        } finally {
            CFRelease(dictionary)
        }
    }

    private fun String.toCFString(): CFStringRef =
        CFStringCreateWithCString(null, this, kCFStringEncodingUTF8)
            ?: throw SecureTokenStorageException("Unable to encode a Keychain attribute")

    private fun ByteArray.toCFData(): CFDataRef = if (isEmpty()) {
        CFDataCreate(null, null, 0)
    } else {
        usePinned { pinned ->
            CFDataCreate(null, pinned.addressOf(0).reinterpret<UByteVar>(), size.toLong())
        }
    } ?: throw SecureTokenStorageException("Unable to encode protected session data")

    private fun CFDataRef.toByteArray(): ByteArray {
        val byteCount = CFDataGetLength(this)
        if (byteCount < 0 || byteCount > MAX_KEYCHAIN_VALUE_BYTES) {
            throw SecureTokenStorageException("Keychain session data has an invalid size")
        }
        if (byteCount == 0L) return byteArrayOf()
        return ByteArray(byteCount.toInt()).also { copy ->
            copy.usePinned { pinned ->
                CFDataGetBytes(
                    this,
                    cValue<CFRange> {
                        location = 0
                        length = byteCount
                    },
                    pinned.addressOf(0).reinterpret<UByteVar>(),
                )
            }
        }
    }

    private fun keychainFailure(operation: String, status: Int) =
        SecureTokenStorageException("Keychain $operation failed with status $status")

    private companion object {
        const val SERVICE = "ma.taximobile.session"
        const val SESSION_ACCOUNT = "session-v1"
        const val LEGACY_ACCESS_ACCOUNT = "access-token"
        const val LEGACY_REFRESH_ACCOUNT = "refresh-token"
        const val MAX_KEYCHAIN_VALUE_BYTES = 128L * 1024L + 9L
    }
}
