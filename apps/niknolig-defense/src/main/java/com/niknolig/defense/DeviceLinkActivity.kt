package com.niknolig.defense

import android.app.Activity
import android.app.AlertDialog
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import org.niknolig.devicelink.AppAreaClaim
import org.niknolig.devicelink.DeviceLinkException
import org.niknolig.devicelink.DeviceLinkGate
import org.niknolig.devicelink.DeviceLinkScopes
import org.niknolig.devicelink.DeviceLinkService
import org.niknolig.devicelink.DiscoveryAnnouncement
import org.niknolig.devicelink.GrantInfo
import org.niknolig.devicelink.HttpsTransport
import org.niknolig.devicelink.LinkInfo
import org.niknolig.devicelink.PairingQr
import org.niknolig.devicelink.PairingState

/**
 * Real device pairing and link management against the backend device API.
 * Every state shown here comes from a backend response; nothing is simulated.
 */
class DeviceLinkActivity : Activity() {
    private val executor: ExecutorService = Executors.newSingleThreadExecutor()
    private val pollExecutor: ExecutorService = Executors.newSingleThreadExecutor()
    private val ui = Handler(Looper.getMainLooper())
    private lateinit var store: PrefsLinkStateStore
    private lateinit var signer: DeviceKey
    private lateinit var nearby: NearbyPairing
    private var service: DeviceLinkService? = null

    private lateinit var statusView: TextView
    private lateinit var signInBox: LinearLayout
    private lateinit var connectedBox: LinearLayout
    private lateinit var pairingView: TextView
    private lateinit var linksBox: LinearLayout
    private lateinit var qrView: ImageView
    private lateinit var nearbyView: TextView
    private lateinit var keyInfoView: TextView
    private lateinit var emailInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var codeInput: EditText

    private var activePairingId: String? = null
    private var confirmedPairingId: String? = null
    private var offeredCode: String? = null
    private var confirmDialog: AlertDialog? = null
    private var polling = false
    @Volatile private var started = false
    @Volatile private var lifecycleGeneration = 0L
    private var pendingScanCode: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = PrefsLinkStateStore(this, DeviceLinkProfile.STATE_KEY_ALIAS)
        // Pairing codes and QR codes must not end up in screenshots or the recents thumbnail.
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        signer = DeviceKeys.open(this, DeviceLinkProfile.DEVICE_KEY_ALIAS, DeviceLinkProfile.SEED_KEY_ALIAS)
        nearby = NearbyPairing(this, DeviceLinkProfile.APP_AREA, deviceName()) { peers -> showNearby(peers) }
        val backend = BuildConfig.BACKEND_BASE_URL
        if (backend.startsWith("https://", ignoreCase = true)) {
            service = DeviceLinkService(
                DeviceLinkGate(BuildConfig.DEVICE_LINK_P0_APPROVED),
                HttpsTransport(backend),
                signer,
                store,
            )
        }
        buildLayout()
    }

    override fun onStart() {
        super.onStart()
        started = true
        lifecycleGeneration++
        refresh()
        if (BuildConfig.DEVICE_LINK_P0_APPROVED && store.deviceId() != null) nearby.startDiscovery()
        pendingScanCode?.let {
            pendingScanCode = null
            claimWith(it)
        }
    }

    override fun onStop() {
        started = false
        lifecycleGeneration++
        polling = false
        confirmDialog?.dismiss()
        confirmDialog = null
        abandonPairing()
        nearby.stop()
        super.onStop()
    }

    /** A pending pairing is cancelled when the screen is left; the one-time code is never kept around. */
    private fun abandonPairing() {
        val pairingId = activePairingId ?: return
        activePairingId = null
        confirmedPairingId = null
        offeredCode = null
        hideOffer()
        val svc = service
        if (svc != null && !executor.isShutdown) {
            executor.execute { runCatching { svc.cancelPairing(pairingId) } }
        }
        setPairingText(getString(R.string.device_link_no_pairing))
    }

    override fun onDestroy() {
        executor.shutdownNow()
        pollExecutor.shutdownNow()
        super.onDestroy()
    }

    private fun buildLayout() {
        val padding = resources.getDimensionPixelSize(R.dimen.screen_padding)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }
        root.addView(text(R.string.device_link_heading, 26f, R.color.text_primary, bold = true).also(::markHeading))
        root.addView(text(R.string.device_link_intro, 15f, R.color.text_secondary))
        statusView = text(R.string.device_link_status_checking, 16f, R.color.brand_accent, bold = true)
        root.addView(statusView)

        signInBox = box()
        signInBox.addView(text(R.string.device_link_signin_hint, 14f, R.color.text_secondary))
        emailInput = input(R.string.device_link_email, InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS)
        passwordInput = input(R.string.device_link_password, InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        signInBox.addView(emailInput)
        signInBox.addView(passwordInput)
        signInBox.addView(button(R.string.device_link_register_button) { register() })
        root.addView(signInBox)

        connectedBox = box()
        connectedBox.addView(button(R.string.device_link_create_code_button) { startPairing() })
        codeInput = input(R.string.device_link_code_hint, InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS)
        connectedBox.addView(codeInput)
        connectedBox.addView(button(R.string.device_link_claim_button) { claim() })
        connectedBox.addView(button(R.string.device_link_scan_button) { scanQr() })
        nearbyView = text("", 14f, R.color.brand_accent).apply { visibility = View.GONE }
        connectedBox.addView(nearbyView)
        pairingView = text(R.string.device_link_no_pairing, 15f, R.color.text_primary)
        connectedBox.addView(pairingView)
        qrView = ImageView(this).apply {
            visibility = View.GONE
            contentDescription = getString(R.string.device_link_qr_description)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
            margin(this, 12)
        }
        connectedBox.addView(qrView)
        keyInfoView = text(
            if (signer.mode == DeviceKeys.MODE_KEYSTORE) R.string.device_link_key_info_keystore
            else R.string.device_link_key_info_software,
            13f, R.color.text_secondary,
        )
        connectedBox.addView(keyInfoView)
        connectedBox.addView(text(R.string.device_link_links_heading, 18f, R.color.gold, bold = true).also(::markHeading))
        linksBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        connectedBox.addView(linksBox)
        connectedBox.addView(button(R.string.device_link_refresh_button) { refresh() })
        connectedBox.addView(button(R.string.device_link_revoke_device_button) { confirmRevokeDevice() })
        root.addView(connectedBox)

        setContentView(ScrollView(this).apply {
            setBackgroundColor(getColor(R.color.dark_background))
            isFillViewport = true
            addView(root)
        })
    }

    // ---- actions ---------------------------------------------------------------------------------

    private fun refresh() {
        val svc = prerequisites() ?: return
        val generation = lifecycleGeneration
        background {
            if (!svc.isRegistered) {
                onUi {
                    if (!isCurrentLifecycle(generation)) return@onUi
                    signInBox.visibility = View.VISIBLE
                    connectedBox.visibility = View.GONE
                    setStatus(R.string.device_link_status_not_registered)
                }
                return@background
            }
            // The server lists expired links too; their grants are gone (404), so only active links count.
            val links = svc.links().filter { it.state == "active" }
            val grants = links.associate { link ->
                link.linkId to try {
                    svc.grants(link.linkId)
                } catch (error: DeviceLinkException) {
                    if (error.statusCode != 404) throw error
                    emptyList()
                }
            }
            // Diagnostics leave the device only while an active outgoing status:read grant exists.
            val sharing = grants.values.any { list ->
                list.any { it.direction == "given" && it.scope == DeviceLinkScopes.STATUS_READ }
            }
            if (sharing) DeviceLinkProfile.statusReport(this)?.let { svc.reportStatus(it.first, it.second) }
            onUi {
                if (!isCurrentLifecycle(generation)) return@onUi
                signInBox.visibility = View.GONE
                connectedBox.visibility = View.VISIBLE
                nearby.startDiscovery()
                renderLinks(links, grants)
                setStatus(
                    if (links.isEmpty()) getString(R.string.device_link_status_registered)
                    else getString(R.string.device_link_status_linked, links.size),
                )
            }
        }
    }

    private fun register() {
        val svc = prerequisites() ?: return
        val email = emailInput.text.toString().trim()
        val password = passwordInput.text.toString()
        if (email.isEmpty() || password.isEmpty()) {
            setStatus(R.string.device_link_error_credentials_missing)
            return
        }
        setStatus(R.string.device_link_status_registering)
        background {
            val result = AccountSignIn(BuildConfig.ACCOUNT_AUTH_URL, BuildConfig.ACCOUNT_AUTH_KEY).signIn(email, password)
            val token = when (result) {
                is AccountSignInResult.Success -> result.accessToken
                else -> {
                    onUi {
                        setStatus(
                            when (result) {
                                AccountSignInResult.NotConfigured -> R.string.device_link_error_account_not_configured
                                AccountSignInResult.InvalidCredentials -> R.string.device_link_error_credentials
                                AccountSignInResult.TimedOut -> R.string.device_link_error_timeout
                                AccountSignInResult.NetworkError -> R.string.device_link_error_offline
                                else -> R.string.device_link_error_generic
                            },
                        )
                    }
                    return@background
                }
            }
            AppAreaClaim.require(token, DeviceLinkProfile.APP_AREA, System.currentTimeMillis() / 1000)
            svc.register(token, DeviceLinkProfile.APP_AREA, store.installationId(), deviceName())
            onUi { passwordInput.setText("") }
            refresh()
        }
    }

    private fun startPairing() {
        val svc = prerequisites() ?: return
        if (!started) return
        val generation = lifecycleGeneration
        background {
            val offer = svc.createPairing()
            if (!isCurrentLifecycle(generation)) {
                runCatching { svc.cancelPairing(offer.pairingId) }
                return@background
            }
            activePairingId = offer.pairingId
            confirmedPairingId = null
            offeredCode = offer.code
            onUi {
                if (!isCurrentLifecycle(generation)) return@onUi
                pairingView.text = getString(R.string.device_link_code_shown, offer.code)
                showOffer(PairingQr(offer.code, DeviceLinkProfile.APP_AREA).encode())
                nearby.startAdvertising()
            }
            poll(svc, offer.pairingId)
        }
    }

    private fun claim() {
        val code = codeInput.text.toString().trim()
        if (code.isEmpty()) {
            setStatus(R.string.device_link_error_code_missing)
            return
        }
        claimWith(code)
    }

    private fun claimWith(code: String) {
        val svc = prerequisites() ?: return
        background {
            val state = svc.claimPairing(code)
            activePairingId = state.pairingId
            confirmedPairingId = null
            offeredCode = null
            onUi { codeInput.setText("") }
            showPairing(svc, state)
            poll(svc, state.pairingId)
        }
    }

    private fun poll(svc: DeviceLinkService, pairingId: String) {
        polling = true
        if (pollExecutor.isShutdown) return
        // A dedicated thread keeps confirm/cancel actions from queuing behind the polling loop.
        pollExecutor.execute {
            var failures = 0
            while (polling && started && activePairingId == pairingId) {
                try {
                    val state = svc.pairing(pairingId)
                    failures = 0
                    showPairing(svc, state)
                    if (state.state != "open" && state.state != "claimed") return@execute
                    Thread.sleep(POLL_INTERVAL_MILLIS)
                } catch (_: InterruptedException) {
                    return@execute
                } catch (error: Exception) {
                    onUi { setStatus(error.deviceLinkMessage()) }
                    if (++failures >= MAX_POLL_FAILURES) return@execute
                    try {
                        Thread.sleep(POLL_INTERVAL_MILLIS)
                    } catch (_: InterruptedException) {
                        return@execute
                    }
                }
            }
        }
    }

    private fun showPairing(svc: DeviceLinkService, state: PairingState) {
        onUi {
            when (state.state) {
                "open" -> setPairingText(
                    offeredCode?.let { getString(R.string.device_link_code_shown, it) }
                        ?: getString(R.string.device_link_waiting_for_peer),
                )
                "claimed" -> {
                    offeredCode = null
                    hideOffer()
                    val peer = state.peer?.displayName.orEmpty()
                    setPairingText(getString(R.string.device_link_compare_codes, peer, state.shortAuthString.orEmpty()))
                    if (!state.confirmedByMe) {
                        askConfirmation(svc, state)
                    }
                }
                "confirmed" -> {
                    setPairingText(getString(R.string.device_link_pairing_done))
                    activePairingId = null
                    hideOffer()
                    refresh()
                }
                "expired" -> endPairing(R.string.device_link_pairing_expired)
                else -> endPairing(R.string.device_link_pairing_cancelled)
            }
        }
    }

    private fun askConfirmation(svc: DeviceLinkService, state: PairingState) {
        if (confirmedPairingId == state.pairingId) return
        confirmedPairingId = state.pairingId
        confirmDialog = AlertDialog.Builder(this)
            .setTitle(R.string.device_link_confirm_title)
            .setMessage(getString(R.string.device_link_confirm_message, state.peer?.displayName.orEmpty(), state.shortAuthString.orEmpty()))
            .setPositiveButton(R.string.device_link_confirm_yes) { _, _ ->
                background {
                    try {
                        showPairing(svc, svc.confirmPairing(state.pairingId))
                    } catch (error: Exception) {
                        confirmedPairingId = null // lets the next poll offer a retry
                        throw error
                    }
                }
            }
            .setNegativeButton(R.string.device_link_confirm_no) { _, _ ->
                background {
                    try {
                        svc.cancelPairing(state.pairingId)
                    } catch (error: Exception) {
                        confirmedPairingId = null
                        throw error
                    }
                    activePairingId = null
                    onUi { endPairing(R.string.device_link_pairing_cancelled) }
                }
            }
            .setCancelable(false)
            .show()
    }

    private fun scanQr() {
        if (prerequisites() == null) return
        PairingQrSupport.scan(
            this,
            onResult = { raw ->
                if (raw != null) {
                    val qr = PairingQr.parse(raw, DeviceLinkProfile.APP_AREA)
                    when {
                        qr == null -> setStatus(R.string.device_link_scan_invalid)
                        started -> claimWith(qr.code)
                        else -> pendingScanCode = qr.code // the scanner screen is still closing; claim in onStart
                    }
                }
            },
            onUnavailable = { setStatus(R.string.device_link_scan_unavailable) },
        )
    }

    private fun showOffer(payload: String) {
        val size = (240 * resources.displayMetrics.density).toInt()
        qrView.setImageBitmap(PairingQrSupport.render(payload, size))
        qrView.visibility = View.VISIBLE
    }

    private fun hideOffer() {
        onUi {
            qrView.setImageDrawable(null)
            qrView.visibility = View.GONE
        }
        nearby.stopAdvertising()
    }

    private fun showNearby(peers: List<DiscoveryAnnouncement>) {
        if (peers.isEmpty()) {
            nearbyView.visibility = View.GONE
            return
        }
        nearbyView.text = getString(R.string.device_link_nearby, peers.joinToString { it.displayName })
        nearbyView.visibility = View.VISIBLE
    }

    private fun endPairing(message: Int) {
        activePairingId = null
        offeredCode = null
        hideOffer()
        polling = false
        setPairingText(getString(message))
    }

    private fun renderLinks(links: List<LinkInfo>, grants: Map<String, List<GrantInfo>>) {
        linksBox.removeAllViews()
        if (links.isEmpty()) {
            linksBox.addView(text(R.string.device_link_no_links, 15f, R.color.text_secondary))
            return
        }
        for (link in links) {
            val card = box()
            card.addView(text(
                getString(R.string.device_link_link_title, link.peer.displayName, link.peer.fingerprint.take(8)),
                16f, R.color.text_primary, bold = true,
            ))
            card.addView(text(getString(R.string.device_link_link_expires, link.expiresAt), 13f, R.color.text_secondary))
            card.addView(button(R.string.device_link_peer_status_button) { showPeerStatus(link) })
            card.addView(button(R.string.device_link_grant_status_button) { grantStatus(link) })
            for (grant in grants[link.linkId].orEmpty().filter { it.direction == "given" }) {
                card.addView(button(getString(R.string.device_link_revoke_grant_button, grant.scope)) {
                    val svc = prerequisites() ?: return@button
                    background { svc.revokeGrant(grant.grantId); refresh() }
                })
            }
            card.addView(button(R.string.device_link_disconnect_button) {
                val svc = prerequisites() ?: return@button
                background { svc.revokeLink(link.linkId); refresh() }
            })
            linksBox.addView(card)
        }
    }

    private fun showPeerStatus(link: LinkInfo) {
        val svc = prerequisites() ?: return
        background {
            val status = svc.peerStatus(link.linkId)
            onUi {
                setStatus(getString(R.string.device_link_peer_status, link.peer.displayName, status.state, status.detail.orEmpty()))
            }
        }
    }

    private fun grantStatus(link: LinkInfo) {
        val svc = prerequisites() ?: return
        background {
            svc.createGrant(link.linkId, DeviceLinkScopes.STATUS_READ, GRANT_SECONDS)
            refresh()
        }
    }

    private fun confirmRevokeDevice() {
        AlertDialog.Builder(this)
            .setTitle(R.string.device_link_revoke_device_title)
            .setMessage(R.string.device_link_revoke_device_message)
            .setPositiveButton(R.string.device_link_revoke_device_yes) { _, _ ->
                val svc = prerequisites() ?: return@setPositiveButton
                background {
                    svc.revokeThisDevice()
                    signer.deleteKey()
                    DeviceKeys.reset(this)
                    onUi {
                        Toast.makeText(this, R.string.device_link_status_revoked, Toast.LENGTH_LONG).show()
                        recreate() // reopens the activity with a fresh key and an unregistered state
                    }
                }
            }
            .setNegativeButton(R.string.device_link_confirm_no, null)
            .show()
    }

    // ---- helpers ---------------------------------------------------------------------------------

    /** Returns the service only when every precondition holds; otherwise shows the reason. */
    private fun prerequisites(): DeviceLinkService? {
        if (!BuildConfig.DEVICE_LINK_P0_APPROVED) {
            setStatus(R.string.device_link_error_blocked)
            hideActions()
            return null
        }
        val svc = service
        if (svc == null) {
            setStatus(R.string.device_link_error_backend_missing)
            hideActions()
            return null
        }
        return svc
    }

    private fun hideActions(): Unit = onUi {
        signInBox.visibility = View.GONE
        connectedBox.visibility = View.GONE
    }

    private fun background(block: () -> Unit) {
        if (executor.isShutdown) return
        executor.execute {
            try {
                block()
            } catch (error: Exception) {
                onUi { setStatus(error.deviceLinkMessage()) }
            }
        }
    }

    private fun onUi(block: () -> Unit) {
        ui.post { if (!isFinishing && !isDestroyed) block() }
    }

    private fun isCurrentLifecycle(generation: Long): Boolean =
        started && lifecycleGeneration == generation

    private fun setStatus(resource: Int): Unit = setStatus(getString(resource))

    private fun setStatus(message: String): Unit = onUi { statusView.text = message }

    private fun setPairingText(message: String) {
        pairingView.text = message
    }

    private fun deviceName(): String =
        "${Build.MANUFACTURER} ${Build.MODEL}".trim().take(64).filter { it >= ' ' && it != '\u007f' }.ifEmpty { "Android" }

    private fun markHeading(view: TextView) {
        if (Build.VERSION.SDK_INT >= 28) view.isAccessibilityHeading = true
    }

    private fun margin(view: View, top: Int = 8) {
        view.layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT,
        ).apply { topMargin = (top * resources.displayMetrics.density).toInt() }
    }

    private fun text(resource: Int, size: Float, color: Int, bold: Boolean = false): TextView =
        text(getString(resource), size, color, bold)

    private fun text(value: String, size: Float, color: Int, bold: Boolean = false): TextView = TextView(this).apply {
        text = value
        textSize = size
        setTextColor(getColor(color))
        if (bold) setTypeface(typeface, android.graphics.Typeface.BOLD)
        margin(this, 12)
    }

    private fun button(resource: Int, onClick: () -> Unit): Button = button(getString(resource), onClick)

    private fun button(label: String, onClick: () -> Unit): Button = Button(this).apply {
        text = label
        setOnClickListener { onClick() }
        margin(this)
    }

    private fun input(hint: Int, type: Int) = EditText(this).apply {
        setHint(hint)
        inputType = type
        setSingleLine()
        setTextColor(getColor(R.color.text_primary))
        setHintTextColor(getColor(R.color.text_secondary))
        importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO
        margin(this)
    }

    private fun box() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        margin(this, 16)
    }

    private companion object {
        const val POLL_INTERVAL_MILLIS = 3_000L
        const val MAX_POLL_FAILURES = 5
        const val GRANT_SECONDS = 24L * 3600
    }
}
