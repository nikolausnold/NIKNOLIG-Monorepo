package com.niknolig.defense

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Bundle
import android.security.NetworkSecurityPolicy
import android.text.format.DateFormat
import android.widget.Button
import android.widget.TextView
import java.util.Date

internal fun Context.connectionLog() = ConnectionLog(
    SharedPreferencesText(getSharedPreferences("connection_log", Context.MODE_PRIVATE), "events"),
)

internal fun Context.declaredPermissions(): List<String> = runCatching {
    @Suppress("DEPRECATION")
    packageManager.getPackageInfo(packageName, PackageManager.GET_PERMISSIONS)
        .requestedPermissions?.toList().orEmpty()
}.getOrDefault(emptyList())

internal fun Context.formatTime(millis: Long): String =
    DateFormat.getMediumDateFormat(this).format(Date(millis)) + " " +
        DateFormat.getTimeFormat(this).format(Date(millis))

internal fun BackendHealthResult.toConnectionCode(): ConnectionCode = when (this) {
    BackendHealthResult.Ready -> ConnectionCode.READY
    BackendHealthResult.NotConfigured -> ConnectionCode.NOT_CONFIGURED
    BackendHealthResult.InvalidResponse -> ConnectionCode.INVALID_RESPONSE
    BackendHealthResult.TimedOut -> ConnectionCode.TIMED_OUT
    BackendHealthResult.NetworkError -> ConnectionCode.NETWORK_ERROR
    is BackendHealthResult.HttpError -> ConnectionCode.HTTP_ERROR
}

class DeviceStatusActivity : Activity() {
    private val log by lazy { connectionLog() }
    private lateinit var networkStatus: TextView
    private lateinit var lastConnection: TextView
    private lateinit var checkButton: Button
    private val checkObserver: (ConnectionCheckState) -> Unit = { state ->
        runOnUiThread {
            if (::checkButton.isInitialized && !isFinishing && !isDestroyed) renderCheckState(state)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_device_status)
        networkStatus = findViewById(R.id.device_network_status)
        lastConnection = findViewById(R.id.device_last_connection)
        checkButton = findViewById(R.id.device_check_button)

        findViewById<TextView>(R.id.device_app_status).text = getString(
            R.string.device_status_app,
            getString(R.string.app_name),
            packageManager.getPackageInfo(packageName, 0).versionName.orEmpty(),
        )

        val permissions = declaredPermissions()
        findViewById<TextView>(R.id.device_permission_status).text =
            if (permissions == listOf("android.permission.INTERNET")) {
                getString(R.string.device_status_permissions_ok)
            } else {
                getString(R.string.device_status_permissions_unexpected, permissions.joinToString())
            }

        val gate = PairingGate.evaluate() as? PairingGate.Blocked
        findViewById<TextView>(R.id.device_pairing_gate).text =
            getString(R.string.device_status_pairing_blocked, gate?.blockers?.size ?: 0)
        findViewById<Button>(R.id.device_pair_button).setOnClickListener { showPairingBlockers(gate) }

        checkButton.setOnClickListener { checkConnection() }
        findViewById<Button>(R.id.device_security_button).setOnClickListener {
            startActivity(Intent(this, SecurityActivity::class.java))
        }
        findViewById<Button>(R.id.device_close_button).setOnClickListener { finish() }

        showLastSuccess()
    }

    override fun onResume() {
        super.onResume()
        if (::lastConnection.isInitialized) {
            showLastSuccess()
            ConnectionCheckCoordinator.observe(checkObserver)
        }
    }

    override fun onPause() {
        ConnectionCheckCoordinator.remove(checkObserver)
        super.onPause()
    }

    private fun showLastSuccess() {
        val state = log.state()
        val last = state.lastSuccessMillis
        val value = if (last == null) getString(R.string.device_status_last_success_none)
        else getString(R.string.device_status_last_success, formatTime(last))
        lastConnection.text = if (state.historyComplete) value
        else "$value\n${getString(R.string.device_status_history_incomplete)}"
    }

    private fun checkConnection() {
        ConnectionCheckCoordinator.start(applicationContext, BuildConfig.BACKEND_BASE_URL)
    }

    private fun renderCheckState(state: ConnectionCheckState) {
        checkButton.isEnabled = !state.isChecking
        val result = state.result
        networkStatus.setText(
            if (state.isChecking) R.string.support_backend_checking
            else result?.let {
                when (it) {
                    BackendHealthResult.Ready -> R.string.support_backend_ready
                    BackendHealthResult.NotConfigured -> R.string.support_backend_not_configured
                    BackendHealthResult.InvalidResponse -> R.string.support_backend_invalid_response
                    BackendHealthResult.TimedOut -> R.string.support_backend_timeout
                    BackendHealthResult.NetworkError -> R.string.support_backend_network_error
                    is BackendHealthResult.HttpError -> R.string.support_backend_http_error
                }
            } ?: R.string.device_status_network_unchecked,
        )
        showLastSuccess()
    }

    private fun showPairingBlockers(gate: PairingGate.Blocked?) {
        val message = gate?.blockers.orEmpty().joinToString("\n\n") { "• " + getString(it.messageRes()) }
        AlertDialog.Builder(this)
            .setTitle(R.string.device_status_pairing_dialog_title)
            .setMessage(message)
            .setPositiveButton(android.R.string.ok, null)
            .show()
    }
}

internal fun PairingBlocker.messageRes(): Int = when (this) {
    PairingBlocker.SECURITYCHAIN_P0_NOT_APPROVED -> R.string.blocker_p0
    PairingBlocker.TRANSPORT_NOT_SELECTED -> R.string.blocker_transport
    PairingBlocker.PEER_IDENTITY_NOT_APPROVED -> R.string.blocker_identity
    PairingBlocker.CONSENT_AND_REVOCATION_NOT_APPROVED -> R.string.blocker_consent
    PairingBlocker.AUDIT_POLICY_NOT_APPROVED -> R.string.blocker_audit
    PairingBlocker.TWO_DEVICE_ACCEPTANCE_MISSING -> R.string.blocker_acceptance
}

internal fun Context.runtimeSecurityChecks(): List<SecurityCheck> {
    val flags = applicationInfo.flags
    return listOf(
        SecurityCheck(SecurityCheckId.BACKUP_FLAG_DISABLED, flags and ApplicationInfo.FLAG_ALLOW_BACKUP == 0),
        SecurityCheck(
            SecurityCheckId.CLEARTEXT_BLOCKED,
            !NetworkSecurityPolicy.getInstance().isCleartextTrafficPermitted,
        ),
        SecurityCheck(SecurityCheckId.NOT_DEBUGGABLE, flags and ApplicationInfo.FLAG_DEBUGGABLE == 0),
        SecurityCheck(
            SecurityCheckId.BACKEND_HTTPS,
            BuildConfig.BACKEND_BASE_URL.isBlank() ||
                BuildConfig.BACKEND_BASE_URL.startsWith("https://", ignoreCase = true),
        ),
        SecurityCheck(
            SecurityCheckId.ONLY_INTERNET_PERMISSION,
            declaredPermissions() == listOf("android.permission.INTERNET"),
        ),
    )
}
