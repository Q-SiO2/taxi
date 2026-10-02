package org.example.taximobile.data.auth

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Host tests use a cipher seam, never pretend to exercise real Keystore. */
internal interface AndroidSessionCipher {
    fun encrypt(plaintext: ByteArray): String
    fun decrypt(record: String): ByteArray
}

internal class AndroidKeystoreSessionCipher : AndroidSessionCipher {
    override fun encrypt(plaintext: ByteArray): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key(createIfMissing = true))
        val ciphertext = Base64.encodeToString(cipher.doFinal(plaintext), Base64.NO_WRAP)
        val iv = Base64.encodeToString(cipher.iv, Base64.NO_WRAP)
        return "$iv:$ciphertext"
    }

    override fun decrypt(record: String): ByteArray {
        require(record.length <= MAX_RECORD_CHARACTERS)
        val parts = record.split(":", limit = 2)
        require(parts.size == 2)
        val iv = Base64.decode(parts[0], Base64.NO_WRAP)
        val ciphertext = Base64.decode(parts[1], Base64.NO_WRAP)
        require(iv.size == 12 && ciphertext.size >= 16)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        // Never generate a replacement key while reading existing ciphertext.
        cipher.init(Cipher.DECRYPT_MODE, key(createIfMissing = false), GCMParameterSpec(128, iv))
        return cipher.doFinal(ciphertext)
    }

    private fun key(createIfMissing: Boolean): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        val existing = keyStore.getKey(KEY_ALIAS, null)
        if (existing != null) {
            check(existing is SecretKey)
            return existing
        }
        check(createIfMissing)
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val KEY_ALIAS = "taximobile.session.aes.v1"
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        // Two bounded 64 KiB tokens, envelope/tag/IV and Base64 expansion.
        const val MAX_RECORD_CHARACTERS = 192_000
    }
}
