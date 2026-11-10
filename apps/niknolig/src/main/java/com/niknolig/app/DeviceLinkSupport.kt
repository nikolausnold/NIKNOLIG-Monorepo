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
import java.security.SecureRandom
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.net.ssl.HttpsURLConnection
import org.niknolig.devicelink.AppAreaClaimException
import org.niknolig.devicelink.DeviceLinkBlockedException
import org.niknolig.devicelink.DeviceLinkException
import org.niknolig.devicelink.DeviceLinkNetworkException
import org.niknolig.devicelink.DeviceLinkNotRegisteredException
import org.niknolig.devicelink.DeviceLinkProtocolException
import org.niknolig.devicelink.DeviceSession
import org.niknolig.devicelink.DeviceSigner
import org.niknolig.devicelink.Json
import org.niknolig.devicelink.LinkStateStore
import org.niknolig.devicelink.SoftwareEd25519Signer

private const val ANDROID_KEYSTORE = "AndroidKeyStore"

/** Device identity key. Which implementation is used is fixed per installation, see [DeviceKeys]. */
internal interface DeviceKey : DeviceSigner {
    /** Persisted key origin: "keystore" (hardware/TEE Ed25519, Android 13+) or "software" (wrapped seed). */
    val mode: String

    /** Removes the key material; the device identity must be registered again afterwards. */
    fun deleteKey()
}

/** Non-exportable Ed25519 device key in the Android Keystore (requires Android 13 / API 33). */
internal class KeystoreDeviceSigner(private val alias: String) : DeviceKey {
    override val mode: String = DeviceKeys.MODE_KEYSTORE

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

    override fun deleteKey() {
        if (keyStore.containsAlias(alias)) keyStore.deleteEntry(alias)
    }

    fun exists(): Boolean = keyStore.containsAlias(alias)

    companion object {
        private const val ED25519_SPKI_BYTES = 44
        fun isSupported(): Boolean = Build.VERSION.SDK_INT >= 33
    }
}

/** AES-GCM sealing under a non-exportable Android Keystore key (Android 6+). Output is IV || ciphertext. */
internal class KeystoreSealer(private val alias: String) {
    private val keyStore: KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    fun seal(plain: ByteArray): ByteArray {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        return cipher.iv + cipher.doFinal(plain)
    }

    fun open(sealed: ByteArray): ByteArray {
        require(sealed.size > IV_BYTES) { "Sealed data too short" }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, sealed, 0, IV_BYTES))
        return cipher.doFinal(sealed, IV_BYTES, sealed.size - IV_BYTES)
    }

    fun delete() {
        if (keyStore.containsAlias(alias)) keyStore.deleteEntry(alias)
    }

    private fun secretKey(): SecretKey {
        (keyStore.getKey(alias, null) as? SecretKey)?.let { return it }
        val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
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
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_BYTES = 12
    }
}

/**
 * Ed25519 fallback for Android 12 and older (and devices whose Keystore lacks Ed25519). The 32-byte seed is
 * generated with [SecureRandom] and only ever stored sealed by a non-exportable Keystore AES key; it is
 * unwrapped per signature and wiped afterwards. This is software-protected, not hardware-bound Ed25519.
 */
internal class SoftwareDeviceKey(context: Context, private val sealAlias: String) : DeviceKey {
    private val prefs: SharedPreferences =
        context.applicationContext.getSharedPreferences("device_link_key", Context.MODE_PRIVATE)
    private val sealer = KeystoreSealer(sealAlias)
    override val mode: String = DeviceKeys.MODE_SOFTWARE

    private val signer: SoftwareEd25519Signer by lazy { loadOrCreate() }

    override val publicKey: ByteArray get() = signer.publicKey

    override fun sign(message: ByteArray): ByteArray = signer.sign(message)

    private fun loadOrCreate(): SoftwareEd25519Signer = synchronized(prefs) {
        val sealed = prefs.getString(KEY_SEED, null)?.let { Base64.decode(it, Base64.NO_WRAP) }
        val publicKey = prefs.getString(KEY_PUBLIC, null)?.let { Base64.decode(it, Base64.NO_WRAP) }
        if (sealed != null && publicKey != null) {
            return SoftwareEd25519Signer(publicKey) { sealer.open(sealed) }
        }
        val seed = ByteArray(SoftwareEd25519Signer.SEED_BYTES).also { SecureRandom().nextBytes(it) }
        try {
            val newSealed = sealer.seal(seed)
            val newPublic = SoftwareEd25519Signer.publicKeyOf(seed)
            prefs.edit()
                .putString(KEY_SEED, Base64.encodeToString(newSealed, Base64.NO_WRAP))
                .putString(KEY_PUBLIC, Base64.encodeToString(newPublic, Base64.NO_WRAP))
                .commit()
            SoftwareEd25519Signer(newPublic) { sealer.open(newSealed) }
        } finally {
            seed.fill(0)
        }
    }

    override fun deleteKey() {
        prefs.edit().remove(KEY_SEED).remove(KEY_PUBLIC).commit()
        sealer.delete()
    }

    private companion object {
        const val KEY_SEED = "seed"
        const val KEY_PUBLIC = "public"
    }
}

/**
 * Chooses the device key once per installation and persists the choice: the registered public key is bound to
 * the backend identity, so the key type must never change silently. Android 13+ uses a Keystore Ed25519 key when
 * the device really supports it; everything else uses [SoftwareDeviceKey].
 */
internal object DeviceKeys {
    const val MODE_KEYSTORE = "keystore"
    const val MODE_SOFTWARE = "software"
    private const val PREFS = "device_link_key"
    private const val KEY_MODE = "mode"

    fun open(context: Context, deviceAlias: String, sealAlias: String): DeviceKey {
        val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return when (prefs.getString(KEY_MODE, null)) {
            MODE_KEYSTORE -> KeystoreDeviceSigner(deviceAlias)
            MODE_SOFTWARE -> SoftwareDeviceKey(context, sealAlias)
            else -> choose(context, deviceAlias, sealAlias, prefs)
        }
    }

    private fun choose(context: Context, deviceAlias: String, sealAlias: String, prefs: SharedPreferences): DeviceKey {
        val keystoreKey = KeystoreDeviceSigner(deviceAlias)
        val chosen: DeviceKey = when {
            keystoreKey.exists() -> keystoreKey
            KeystoreDeviceSigner.isSupported() -> try {
                // Probe: some Android 13+ devices advertise Ed25519 but fail on key generation or signing.
                keystoreKey.sign(ByteArray(1))
                keystoreKey
            } catch (_: Exception) {
                runCatching { keystoreKey.deleteKey() }
                SoftwareDeviceKey(context, sealAlias)
            }
            else -> SoftwareDeviceKey(context, sealAlias)
        }
        prefs.edit().putString(KEY_MODE, chosen.mode).commit()
        return chosen
    }

    /** Forgets the stored choice; call together with [DeviceKey.deleteKey]. */
    fun reset(context: Context) {
        context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove(KEY_MODE).commit()
    }
}

/** Link state in app-private preferences; session tokens are AES-GCM encrypted with a Keystore key. */
internal class PrefsLinkStateStore(context: Context, private val keyAlias: String) : LinkStateStore {
    private val prefs: SharedPreferences =
        context.applicationContext.getSharedPreferences("device_link_state", Context.MODE_PRIVATE)
    private val sealer = KeystoreSealer(keyAlias)

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
            val parts = String(sealer.open(Base64.decode(sealed, Base64.NO_WRAP)), Charsets.UTF_8).split('\n')
            DeviceSession(parts[0], parts[1])
        }.getOrNull()
    }

    override fun saveSession(session: DeviceSession) {
        val sealed = sealer.seal("${session.accessToken}\n${session.refreshToken}".toByteArray(Charsets.UTF_8))
        prefs.edit().putString(KEY_SESSION, Base64.encodeToString(sealed, Base64.NO_WRAP)).commit()
    }

    override fun clearSession() {
        prefs.edit().remove(KEY_SESSION).commit()
    }

    override fun clear() {
        // A revoked installation id is rejected by the backend, so re-registration needs a fresh one.
        prefs.edit().remove(KEY_SESSION).remove(KEY_DEVICE).remove(KEY_INSTALLATION).commit()
        sealer.delete()
    }

    private companion object {
        const val KEY_INSTALLATION = "installation_id"
        const val KEY_DEVICE = "device_id"
        const val KEY_SESSION = "session"
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
    is AppAreaClaimException -> when (reason) {
        AppAreaClaimException.Reason.MISSING -> R.string.device_link_error_area_missing
        AppAreaClaimException.Reason.MISMATCH -> R.string.device_link_error_area_mismatch
        AppAreaClaimException.Reason.EXPIRED -> R.string.device_link_error_token_expired
    }
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
