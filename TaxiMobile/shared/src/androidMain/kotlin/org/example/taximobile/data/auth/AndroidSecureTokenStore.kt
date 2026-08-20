package org.example.taximobile.data.auth

import android.content.Context
import android.util.Base64
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties

/** Stores only AES-GCM ciphertext in app preferences; the key stays in Android Keystore. */
class AndroidSecureTokenStore(context: Context) : SecureTokenStore {
    private val preferences = context.getSharedPreferences("taximobile.secure_session", Context.MODE_PRIVATE)

    override suspend fun tokens(): StoredTokens? {
        val access = decrypt(preferences.getString(ACCESS_TOKEN, null))
        val refresh = decrypt(preferences.getString(REFRESH_TOKEN, null))
        if (access == null || refresh == null) {
            clear()
            return null
        }
        return StoredTokens(accessToken = access, refreshToken = refresh)
    }

    override suspend fun save(accessToken: String, refreshToken: String) {
        preferences.edit()
            .putString(ACCESS_TOKEN, encrypt(accessToken))
            .putString(REFRESH_TOKEN, encrypt(refreshToken))
            .apply()
    }

    override suspend fun clear() {
        preferences.edit().remove(ACCESS_TOKEN).remove(REFRESH_TOKEN).apply()
    }

    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encoded = Base64.encodeToString(cipher.doFinal(value.toByteArray(StandardCharsets.UTF_8)), Base64.NO_WRAP)
        val iv = Base64.encodeToString(cipher.iv, Base64.NO_WRAP)
        return "$iv:$encoded"
    }

    private fun decrypt(stored: String?): String? = try {
        val parts = stored?.split(":", limit = 2) ?: return null
        if (parts.size != 2) return null
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP)))
        String(cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), StandardCharsets.UTF_8)
    } catch (_: Exception) {
        null
    }

    private fun key(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return generator.generateKey()
    }

    private companion object {
        const val ACCESS_TOKEN = "access_token"
        const val REFRESH_TOKEN = "refresh_token"
        const val KEY_ALIAS = "taximobile.session.aes.v1"
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}
