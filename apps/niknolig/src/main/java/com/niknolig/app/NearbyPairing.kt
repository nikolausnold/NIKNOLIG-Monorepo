package com.niknolig.app

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Handler
import android.os.Looper
import java.net.ServerSocket
import java.security.SecureRandom
import org.niknolig.devicelink.DiscoveryAnnouncement

/**
 * Local-network hints via Android NSD (mDNS). A device that currently offers a pairing announces only its app
 * area and display name; the pairing code is never broadcast. Discovery changes nothing about trust: pairing
 * still needs the code (typed or from the QR) and the mutual confirmation enforced by the backend.
 * All callbacks are delivered on the main thread.
 */
internal class NearbyPairing(
    context: Context,
    private val area: String,
    private val displayName: String,
    private val onPeersChanged: (List<DiscoveryAnnouncement>) -> Unit,
) {
    private val nsd = context.applicationContext.getSystemService(Context.NSD_SERVICE) as NsdManager
    private val handler = Handler(Looper.getMainLooper())
    private val peers = LinkedHashMap<String, DiscoveryAnnouncement>()
    private val present = HashMap<String, NsdServiceInfo>()
    private val pending = ArrayDeque<NsdServiceInfo>()
    private var resolving = false
    private var discoveryGeneration = 0L
    private var registration: NsdManager.RegistrationListener? = null
    private var discovery: NsdManager.DiscoveryListener? = null

    // NSD requires a port. Nothing is ever accepted on it: the socket only reserves the number.
    private var portHolder: ServerSocket? = null

    fun startAdvertising() {
        if (registration != null) return
        val socket = runCatching { ServerSocket(0, 1) }.getOrNull() ?: return
        portHolder = socket
        val info = NsdServiceInfo().apply {
            serviceName = "niknolig-" + ByteArray(4).also { SecureRandom().nextBytes(it) }.joinToString("") { "%02x".format(it) }
            serviceType = DiscoveryAnnouncement.SERVICE_TYPE
            port = socket.localPort
            DiscoveryAnnouncement(area, displayName).txt().forEach { (key, value) -> setAttribute(key, value) }
        }
        val listener = object : NsdManager.RegistrationListener {
            override fun onRegistrationFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                handler.post { stopAdvertising() }
            }
            override fun onUnregistrationFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {}
            override fun onServiceRegistered(serviceInfo: NsdServiceInfo) {}
            override fun onServiceUnregistered(serviceInfo: NsdServiceInfo) {}
        }
        registration = listener
        runCatching { nsd.registerService(info, NsdManager.PROTOCOL_DNS_SD, listener) }.onFailure { stopAdvertising() }
    }

    fun stopAdvertising() {
        registration?.let { runCatching { nsd.unregisterService(it) } }
        registration = null
        runCatching { portHolder?.close() }
        portHolder = null
    }

    fun startDiscovery() {
        if (discovery != null) return
        val generation = ++discoveryGeneration
        lateinit var listener: NsdManager.DiscoveryListener
        listener = object : NsdManager.DiscoveryListener {
            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                handler.post {
                    if (isCurrentDiscovery(generation, listener)) {
                        discovery = null
                        pending.clear()
                        present.clear()
                        resolving = false
                        clearPeers()
                    }
                }
            }
            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {}
            override fun onDiscoveryStarted(serviceType: String) {}
            override fun onDiscoveryStopped(serviceType: String) {}
            override fun onServiceFound(serviceInfo: NsdServiceInfo) {
                handler.post {
                    if (!isCurrentDiscovery(generation, listener)) return@post
                    if (serviceInfo.serviceType.trimEnd('.') == DiscoveryAnnouncement.SERVICE_TYPE.trimEnd('.')) {
                        present[serviceInfo.serviceName] = serviceInfo
                        pending.removeAll { it.serviceName == serviceInfo.serviceName }
                        pending.addLast(serviceInfo)
                        resolveNext()
                    }
                }
            }
            override fun onServiceLost(serviceInfo: NsdServiceInfo) {
                handler.post {
                    if (!isCurrentDiscovery(generation, listener)) return@post
                    present.remove(serviceInfo.serviceName)
                    pending.removeAll { it.serviceName == serviceInfo.serviceName }
                    if (peers.remove(serviceInfo.serviceName) != null) onPeersChanged(peers.values.toList())
                }
            }
        }
        discovery = listener
        runCatching { nsd.discoverServices(DiscoveryAnnouncement.SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, listener) }
            .onFailure {
                if (isCurrentDiscovery(generation, listener)) {
                    discovery = null
                    pending.clear()
                    present.clear()
                    resolving = false
                    clearPeers()
                }
            }
    }

    fun stop() {
        stopAdvertising()
        discoveryGeneration++
        discovery?.let { runCatching { nsd.stopServiceDiscovery(it) } }
        discovery = null
        pending.clear()
        present.clear()
        resolving = false
        peers.clear()
        onPeersChanged(emptyList())
        handler.removeCallbacksAndMessages(null)
    }

    // Older Android versions resolve one service at a time, so resolutions are queued.
    @Suppress("DEPRECATION")
    private fun resolveNext() {
        if (resolving) return
        val listener = discovery ?: return
        val generation = discoveryGeneration
        val info = pending.removeFirstOrNull() ?: return
        resolving = true
        val done = {
            if (isCurrentDiscovery(generation, listener)) {
                resolving = false
                resolveNext()
            }
        }
        runCatching {
            nsd.resolveService(info, object : NsdManager.ResolveListener {
                override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                    handler.post {
                        if (isCurrentDiscovery(generation, listener)) {
                            if (present[info.serviceName] === info) removePeer(info.serviceName)
                            done()
                        }
                    }
                }
                override fun onServiceResolved(serviceInfo: NsdServiceInfo) {
                    handler.post {
                        if (!isCurrentDiscovery(generation, listener)) return@post
                        if (present[info.serviceName] !== info) {
                            done()
                            return@post
                        }
                        val announcement = DiscoveryAnnouncement.parse(serviceInfo.attributes, area)
                        if (announcement == null) removePeer(serviceInfo.serviceName)
                        else {
                            peers[serviceInfo.serviceName] = announcement
                            onPeersChanged(peers.values.toList())
                        }
                        done()
                    }
                }
            })
        }.onFailure { done() }
    }

    private fun isCurrentDiscovery(generation: Long, listener: NsdManager.DiscoveryListener): Boolean =
        discoveryGeneration == generation && discovery === listener

    private fun removePeer(serviceName: String) {
        if (peers.remove(serviceName) != null) onPeersChanged(peers.values.toList())
    }

    private fun clearPeers() {
        if (peers.isNotEmpty()) {
            peers.clear()
            onPeersChanged(emptyList())
        }
    }
}
