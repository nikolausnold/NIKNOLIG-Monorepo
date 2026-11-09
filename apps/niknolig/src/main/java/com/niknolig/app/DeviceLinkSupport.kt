package com.niknolig.app

import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.URL
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.net.ssl.HttpsURLConnection
import org.niknolig.devicelink.DeviceLinkBlockedException
import org.niknolig.devicelink.DeviceLinkException
import org.niknolig.devicelink.DeviceLinkNetworkException
import org.niknolig.devicelink.DeviceLinkNotRegisteredException
import org.niknolig.devicelink.DeviceLinkProtocolException
import org.niknolig.devicelink.DeviceSession
import org.niknolig.devicelink.DeviceSigner
import org.niknolig.devicelink.Json
import org.niknolig.devicelink.LinkStateStore

private const val ANDROID_KEYSTORE = "AndroidKeyStore"

/** Non-exportable Ed25519 device key in the Android Keystore (requires Android 13 / API 33). */
internal class KeystoreDeviceSigner(private val alias: String) : DeviceSigner {
    private val keyStore: KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    override val publicKey: ByteArray
        get() {
            ensureKey()
            val encoded = keyStore.getCertificate(alias).publicKey.encoded
            check(encoded.size == ED25519_SPKI_BYTES) { "Unexpected Ed25519 key encoding" }
            return encoded.copyOfRange(encoded.size - 32, encoded.size)
        }

    override fun sign(message: ByteArray): ByteArray {
        ensureKey()
        val privateKey = keyStore.getKey(alias, null) as PrivateKey
        return Signature.getInstance("Ed25519").run {
            initSign(privateKey)
            update(message)
            sign()
        }
    }

    private fun ensureKey() {
        check(isSupported()) { "Ed25519 device keys need Android 13 or newer" }
        if (keyStore.containsAlias(alias)) return
        val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN)
            .setAlgorithmParameterSpec(ECGenParameterSpec("ed25519"))
            .setDigests(KeyProperties.DIGEST_NONE)
            .build()
        KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, ANDROID_KEYSTORE).run {
            initialize(spec)
            generateKeyPair()
        }
    }

    fun deleteKey() {
        if (keyStore.containsAlias(alias)) keyStore.deleteEntry(alias)
    }

    companion object {
        private const val ED25519_SPKI_BYTES = 44
        fun isSupported(): Boolean = Build.VERSION.SDK_INT >= 33
    }
}

/** Link state in app-private preferences; session tokens are AES-GCM encrypted with a Keystore key. */
internal class PrefsLinkStateStore(context: Context, private val keyAlias: String) : LinkStateStore {
    private val prefs: SharedPreferences =
        context.applicationContext.getSharedPreferences("device_link_state", Context.MODE_PRIVATE)
    private val keyStore: KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    fun installationId(): String = synchronized(this) {
        prefs.getString(KEY_INSTALLATION, null) ?: UUID.randomUUID().toString().also {
            prefs.edit().putString(KEY_INSTALLATION, it).apply()
        }
    }

    override fun deviceId(): String? = prefs.getString(KEY_DEVICE, null)

    override fun saveDeviceId(id: String) {
        prefs.edit().putString(KEY_DEVICE, id).apply()
    }

    override fun session(): DeviceSession? {
        val sealed = prefs.getString(KEY_SESSION, null) ?: return null
        return runCatching {
            val raw = Base64.decode(sealed, Base64.NO_WRAP)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, raw, 0, IV_BYTES))
            val parts = String(cipher.doFinal(raw, IV_BYTES, raw.size - IV_BYTES), Charsets.UTF_8).split('\n')
            DeviceSession(parts[0], parts[1])
        }.getOrNull()
    }

    override fun saveSession(session: DeviceSession) {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val sealed = cipher.iv + cipher.doFinal("${session.accessToken}\n${session.refreshToken}".toByteArray(Charsets.UTF_8))
        prefs.edit().putString(KEY_SESSION, Base64.encodeToString(sealed, Base64.NO_WRAP)).commit()
    }

    override fun clearSession() {
        prefs.edit().remove(KEY_SESSION).commit()
    }

    override fun clear() {
        prefs.edit().remove(KEY_SESSION).remove(KEY_DEVICE).commit()
        if (keyStore.containsAlias(keyAlias)) keyStore.deleteEntry(keyAlias)
    }

    private fun secretKey(): SecretKey {
        (keyStore.getKey(keyAlias, null) as? SecretKey)?.let { return it }
        val spec = KeyGenParameterSpec.Builder(keyAlias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE).run {
            init(spec)
            generateKey()
        }
    }

    private companion object {
        const val KEY_INSTALLATION = "installation_id"
        const val KEY_DEVICE = "device_id"
        const val KEY_SESSION = "session"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_BYTES = 12
    }
}

internal sealed class AccountSignInResult {
    data class Success(val accessToken: String) : AccountSignInResult()
    data object NotConfigured : AccountSignInResult()
    data object InvalidCredentials : AccountSignInResult()
    data object TimedOut : AccountSignInResult()
    data object NetworkError : AccountSignInResult()
    data object Failed : AccountSignInResult()
}

/** Supabase password sign-in. The password and token are used once and never persisted. */
internal class AccountSignIn(private val authUrl: String, private val publicKey: String) {
    fun signIn(email: String, password: String): AccountSignInResult {
        val origin = authUrl.trim().trimEnd('/')
        if (!origin.startsWith("https://", ignoreCase = true) || publicKey.isBlank()) {
            return AccountSignInResult.NotConfigured
        }
        var connection: HttpsURLConnection? = null
        return try {
            connection = URL("$origin/auth/v1/token?grant_type=password").openConnection() as HttpsURLConnection
            connection.connectTimeout = TIMEOUT_MILLIS
            connection.readTimeout = TIMEOUT_MILLIS
            connection.requestMethod = "POST"
            connection.instanceFollowRedirects = false
            connection.useCaches = false
            connection.doOutput = true
            connection.setRequestProperty("apikey", publicKey)
            connection.setRequestProperty("Content-Type", "application/json")
            connection.outputStream.use {
                it.write(Json.encode(mapOf("email" to email, "password" to password)).toByteArray(Charsets.UTF_8))
            }
            when (connection.responseCode) {
                200 -> {
                    val text = connection.inputStream.use { readBounded(it) }
                    val token = Json.decodeObject(text)["access_token"] as? String
                    if (token.isNullOrBlank()) AccountSignInResult.Failed else AccountSignInResult.Success(token)
                }
                400, 401, 403, 422 -> AccountSignInResult.InvalidCredentials
                else -> AccountSignInResult.Failed
            }
        } catch (_: SocketTimeoutException) {
            AccountSignInResult.TimedOut
        } catch (_: IOException) {
            AccountSignInResult.NetworkError
        } catch (_: IllegalArgumentException) {
            AccountSignInResult.Failed
        } finally {
            connection?.disconnect()
        }
    }

    private fun readBounded(input: java.io.InputStream): String {
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(2048)
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            if (output.size() + count > MAX_RESPONSE_BYTES) throw IOException("Response too large")
            output.write(buffer, 0, count)
        }
        return output.toString(Charsets.UTF_8.name())
    }

    private companion object {
        const val TIMEOUT_MILLIS = 8_000
        const val MAX_RESPONSE_BYTES = 32_768
    }
}

/** Maps failures to the string resource shown to the user; no raw server or exception text is displayed. */
internal fun Throwable.deviceLinkMessage(): Int = when (this) {
    is DeviceLinkBlockedException -> R.string.device_link_error_blocked
    is DeviceLinkNotRegisteredException -> R.string.device_link_error_not_registered
    is DeviceLinkNetworkException ->
        if (timedOut) R.string.device_link_error_timeout else R.string.device_link_error_offline
    is DeviceLinkException -> when (statusCode) {
        401 -> R.string.device_link_error_session
        403 -> R.string.device_link_error_forbidden
        404 -> R.string.device_link_error_not_found
        409 -> R.string.device_link_error_conflict
        408, 429 -> R.string.device_link_error_rate_limited
        in 500..599 -> R.string.device_link_error_server
        else -> R.string.device_link_error_generic
    }
    is DeviceLinkProtocolException -> R.string.device_link_error_protocol
    is IllegalStateException -> R.string.device_link_error_key
    else -> R.string.device_link_error_generic
}
