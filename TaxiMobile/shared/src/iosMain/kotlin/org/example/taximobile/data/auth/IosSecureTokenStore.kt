package org.example.taximobile.data.auth

import kotlinx.cinterop.CPointer
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.addressOf
import kotlinx.cinterop.alloc
import kotlinx.cinterop.memScoped
import kotlinx.cinterop.ptr
import kotlinx.cinterop.reinterpret
import kotlinx.cinterop.usePinned
import platform.CoreFoundation.CFDictionaryRef
import platform.CoreFoundation.CFTypeRefVar
import platform.Foundation.NSData
import platform.Foundation.NSString
import platform.Foundation.NSUTF8StringEncoding
import platform.Security.errSecItemNotFound
import platform.Security.errSecSuccess
import platform.Security.kSecAttrAccount
import platform.Security.kSecAttrService
import platform.Security.kSecClass
import platform.Security.kSecClassGenericPassword
import platform.Security.kSecMatchLimit
import platform.Security.kSecMatchLimitOne
import platform.Security.kSecReturnData
import platform.Security.kSecValueData
import platform.Security.SecItemAdd
import platform.Security.SecItemCopyMatching
import platform.Security.SecItemDelete
import platform.posix.memcpy

/** Uses the iOS Keychain; token values never enter user defaults or logs. */
@OptIn(ExperimentalForeignApi::class)
class IosSecureTokenStore : SecureTokenStore {
    override suspend fun tokens(): StoredTokens? {
        val access = read(ACCESS_ACCOUNT)
        val refresh = read(REFRESH_ACCOUNT)
        if (access == null || refresh == null) {
            clear()
            return null
        }
        return StoredTokens(accessToken = access, refreshToken = refresh)
    }

    override suspend fun save(accessToken: String, refreshToken: String) {
        write(ACCESS_ACCOUNT, accessToken)
        write(REFRESH_ACCOUNT, refreshToken)
    }

    override suspend fun clear() {
        delete(ACCESS_ACCOUNT)
        delete(REFRESH_ACCOUNT)
    }

    private fun read(account: String): String? = memScoped {
        val result = alloc<CFTypeRefVar>()
        val status = SecItemCopyMatching(
            query(account, mapOf(kSecReturnData to true, kSecMatchLimit to kSecMatchLimitOne)),
            result.ptr,
        )
        when (status) {
            errSecSuccess -> (result.value as? NSData)?.toUtf8String()
            errSecItemNotFound -> null
            else -> null
        }
    }

    private fun write(account: String, value: String) {
        delete(account)
        SecItemAdd(query(account, mapOf(kSecValueData to value.toNSData())), null)
    }

    private fun delete(account: String) {
        SecItemDelete(query(account))
    }

    private fun query(account: String, extra: Map<Any?, Any?> = emptyMap()): CFDictionaryRef =
        (mapOf<Any?, Any?>(
            kSecClass to kSecClassGenericPassword,
            kSecAttrService to SERVICE,
            kSecAttrAccount to account,
        ) + extra) as CFDictionaryRef

    private fun String.toNSData(): NSData = encodeToByteArray().toNSData()

    private fun ByteArray.toNSData(): NSData = usePinned {
        NSData.create(bytes = it.addressOf(0), length = size.toULong())
    }

    private fun NSData.toUtf8String(): String? {
        val byteCount = length.toInt()
        if (byteCount == 0) return ""
        val copy = ByteArray(byteCount)
        copy.usePinned { destination -> memcpy(destination.addressOf(0), bytes, length) }
        return NSString.create(data = copy.toNSData(), encoding = NSUTF8StringEncoding)?.toString()
    }

    private companion object {
        const val SERVICE = "ma.taximobile.session"
        const val ACCESS_ACCOUNT = "access-token"
        const val REFRESH_ACCOUNT = "refresh-token"
    }
}
