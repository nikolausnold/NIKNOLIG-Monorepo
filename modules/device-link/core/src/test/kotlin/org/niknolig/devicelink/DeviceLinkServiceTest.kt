package org.niknolig.devicelink

import java.util.Base64
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class DeviceLinkServiceTest {
    private class MemoryStore : LinkStateStore {
        var id: String? = null
        var current: DeviceSession? = null
        override fun deviceId() = id
        override fun saveDeviceId(id: String) { this.id = id }
        override fun session() = current
        override fun saveSession(session: DeviceSession) { current = session }
        override fun clearSession() { current = null }
        override fun clear() { id = null; current = null }
    }

    private class Script(val replies: ArrayDeque<TransportResponse>) : DeviceLinkTransport {
        val calls = mutableListOf<Triple<String, String, String?>>()
        val bodies = mutableListOf<Map<String, Any?>?>()
        override fun request(method: String, path: String, bearer: String?, body: Map<String, Any?>?): TransportResponse {
            calls += Triple(method, path, bearer)
            bodies += body
            return replies.removeFirst()
        }
    }

    private val signer = object : DeviceSigner {
        override val publicKey = ByteArray(32)
        override fun sign(message: ByteArray) = ByteArray(64)
    }

    private fun service(store: MemoryStore, vararg replies: TransportResponse, open: Boolean = true): Pair<DeviceLinkService, Script> {
        val transport = Script(ArrayDeque(replies.toList()))
        return DeviceLinkService(DeviceLinkGate(open), transport, signer, store) to transport
    }

    private fun registered() = MemoryStore().apply {
        id = "dev"
        current = DeviceSession("a1", "r1")
    }

    @Test
    fun jsonRoundTripAndStrictness() {
        val text = Json.encode(mapOf("a" to "x\"y\n", "n" to 5L, "z" to null, "b" to true))
        val parsed = Json.decodeObject(text)
        assertEquals("x\"y\n", parsed["a"])
        assertEquals(5L, parsed["n"])
        assertNull(parsed["z"])
        assertEquals(listOf(1L, "x"), Json.decodeObject("{\"l\":[1,\"x\"]}")["l"])
        for (bad in listOf("", "[]", "{", "{\"a\":1} x", "{\"a\":\"\u0001\"}")) {
            try {
                Json.decodeObject(bad); fail(bad)
            } catch (_: IllegalArgumentException) {
            }
        }
    }

    @Test
    fun registerUsesJwtSubjectAndNeverStoresTheUserToken() {
        val payload = Base64.getUrlEncoder().withoutPadding().encodeToString("""{"sub":"user-1"}""".toByteArray())
        val jwt = "h.$payload.s"
        val nonce = DeviceProtocol.b64url(ByteArray(32))
        val store = MemoryStore()
        val (svc, transport) = service(
            store,
            TransportResponse(201, mapOf("id" to "dev")),
            TransportResponse(200, mapOf("nonce" to nonce)),
            TransportResponse(201, mapOf("accessToken" to "a", "refreshToken" to "r")),
        )
        assertEquals("dev", svc.register(jwt, "niknolig", "iid", "Phone"))
        assertEquals(jwt, transport.calls[0].third)
        assertEquals("dev", store.id)
        assertEquals(DeviceSession("a", "r"), store.current)
        assertTrue(transport.calls.drop(1).none { it.third == jwt })
    }

    @Test
    fun expiredAccessTokenIsRefreshedAndRotatedOnce() {
        val store = registered()
        val (svc, transport) = service(
            store,
            TransportResponse(401, emptyMap()),
            TransportResponse(200, mapOf("accessToken" to "a2", "refreshToken" to "r2")),
            TransportResponse(200, mapOf("links" to emptyList<Any>())),
        )
        assertTrue(svc.links().isEmpty())
        assertEquals(DeviceSession("a2", "r2"), store.current)
        assertEquals("a2", transport.calls[2].third)
    }

    @Test
    fun rotatedSessionFromAnotherCallerIsReusedInsteadOfReplayingRefresh() {
        val store = registered()
        val transport = object : DeviceLinkTransport {
            val calls = mutableListOf<Pair<String, String?>>()
            override fun request(method: String, path: String, bearer: String?, body: Map<String, Any?>?): TransportResponse {
                calls += path to bearer
                if (bearer == "a1") {
                    // A concurrent caller renews the shared session while this request is in flight.
                    store.current = DeviceSession("a2", "r2")
                    return TransportResponse(401, emptyMap())
                }
                return TransportResponse(200, mapOf("links" to emptyList<Any>()))
            }
        }
        DeviceLinkService(DeviceLinkGate(true), transport, signer, store).links()
        assertTrue(transport.calls.none { it.first == "/v1/sessions/refresh" })
        assertEquals("a2", transport.calls.last().second)
    }

    @Test
    fun concurrentServiceInstancesShareRefreshRenewalLock() {
        val store = registered()
        val initialRequests = CountDownLatch(2)
        val refreshRequests = AtomicInteger()
        val transport = object : DeviceLinkTransport {
            override fun request(method: String, path: String, bearer: String?, body: Map<String, Any?>?): TransportResponse {
                if (path == "/v1/links" && bearer == "a1") {
                    initialRequests.countDown()
                    check(initialRequests.await(5, TimeUnit.SECONDS))
                    return TransportResponse(401, emptyMap())
                }
                if (path == "/v1/sessions/refresh") {
                    refreshRequests.incrementAndGet()
                    return TransportResponse(200, mapOf("accessToken" to "a2", "refreshToken" to "r2"))
                }
                check(bearer == "a2")
                return TransportResponse(200, mapOf("links" to emptyList<Any>()))
            }
        }
        val services = List(2) { DeviceLinkService(DeviceLinkGate(true), transport, signer, store) }
        val executor = Executors.newFixedThreadPool(2)
        try {
            val results = services.map { service ->
                executor.submit<Boolean> { service.links().isEmpty() }
            }
            results.forEach { assertTrue(it.get(10, TimeUnit.SECONDS)) }
            assertEquals(1, refreshRequests.get())
            assertEquals(DeviceSession("a2", "r2"), store.current)
        } finally {
            executor.shutdownNow()
        }
    }

    @Test
    fun revokedRefreshFallsBackToChallengeSession() {
        val store = registered()
        val nonce = DeviceProtocol.b64url(ByteArray(32))
        val (svc, _) = service(
            store,
            TransportResponse(401, emptyMap()),
            TransportResponse(401, emptyMap()),
            TransportResponse(200, mapOf("nonce" to nonce)),
            TransportResponse(201, mapOf("accessToken" to "a3", "refreshToken" to "r3")),
            TransportResponse(200, mapOf("links" to emptyList<Any>())),
        )
        svc.links()
        assertEquals("a3", store.current?.accessToken)
    }

    @Test
    fun persistentUnauthorizedAndForbiddenSurfaceAsErrors() {
        val (svc, _) = service(
            registered(),
            TransportResponse(401, emptyMap()),
            TransportResponse(200, mapOf("accessToken" to "a2", "refreshToken" to "r2")),
            TransportResponse(401, emptyMap()),
        )
        try {
            svc.links(); fail()
        } catch (error: DeviceLinkException) {
            assertEquals(401, error.statusCode)
        }
        val (svc2, _) = service(registered(), TransportResponse(403, emptyMap()))
        try {
            svc2.revokeLink("l1"); fail()
        } catch (error: DeviceLinkException) {
            assertEquals(403, error.statusCode)
        }
    }

    @Test
    fun parsesPairingStateAndRejectsInjectedIdentifiers() {
        val peer = mapOf("id" to "p", "appArea" to "niknolig-defense", "displayName" to "Defense", "fingerprint" to "ab12")
        val reply = mapOf(
            "pairingId" to "pid", "state" to "claimed", "role" to "initiator", "expiresAt" to "t",
            "peer" to peer, "confirmedByMe" to false, "confirmedByPeer" to true, "linkId" to null,
            "shortAuthString" to "123456",
        )
        val (svc, transport) = service(registered(), TransportResponse(200, reply))
        val state = svc.pairing("pid")
        assertEquals("123456", state.shortAuthString)
        assertEquals("niknolig-defense", state.peer?.appArea)
        assertTrue(state.confirmedByPeer && !state.confirmedByMe)
        assertEquals("/v1/pairings/pid", transport.calls[0].second)
        try {
            svc.pairing("../x"); fail()
        } catch (_: IllegalArgumentException) {
        }
    }

    @Test
    fun grantRequestCarriesScopeAndTtl() {
        val reply = mapOf("grantId" to "g", "linkId" to "l", "scope" to "status:read", "direction" to "given", "expiresAt" to "t")
        val (svc, transport) = service(registered(), TransportResponse(201, reply))
        assertEquals("g", svc.createGrant("l", DeviceLinkScopes.STATUS_READ, 3600).grantId)
        assertEquals(mapOf("scope" to "status:read", "ttlSeconds" to 3600L), transport.bodies[0])
    }

    @Test
    fun revokeThisDeviceClearsLocalStateOnlyAfterServerSuccess() {
        val failing = registered()
        val (svc, _) = service(failing, TransportResponse(500, emptyMap()))
        try {
            svc.revokeThisDevice(); fail()
        } catch (_: DeviceLinkException) {
        }
        assertEquals("dev", failing.id)
        val ok = registered()
        service(ok, TransportResponse(200, mapOf("status" to "revoked"))).first.revokeThisDevice()
        assertNull(ok.id)
        assertNull(ok.current)
    }

    @Test
    fun ownerRecoveryClearsLocalIdentityOnlyAfterServerConfirmsRevocation() {
        val store = registered()
        val transport = Script(ArrayDeque(listOf(TransportResponse(200, mapOf("status" to "revoked")))))
        var keyCleared = false

        DeviceLinkRecovery(DeviceLinkGate(true), transport, store)
            .recoverRevokedDevice("owner-jwt") { keyCleared = true }

        assertEquals(Triple("DELETE", "/v1/devices/dev", "owner-jwt"), transport.calls.single())
        assertTrue(keyCleared)
        assertNull(store.id)
        assertNull(store.current)
    }

    @Test
    fun failedOwnerRecoveryKeepsLocalIdentityAndKey() {
        val store = registered()
        val transport = Script(ArrayDeque(listOf(TransportResponse(503, emptyMap()))))
        var keyCleared = false

        try {
            DeviceLinkRecovery(DeviceLinkGate(true), transport, store)
                .recoverRevokedDevice("owner-jwt") { keyCleared = true }
            fail()
        } catch (error: DeviceLinkException) {
            assertEquals(503, error.statusCode)
        }

        assertEquals("dev", store.id)
        assertEquals(DeviceSession("a1", "r1"), store.current)
        assertTrue(!keyCleared)
    }

    @Test
    fun closedGateBlocksServiceCalls() {
        val (svc, transport) = service(registered(), open = false)
        try {
            svc.links(); fail()
        } catch (_: DeviceLinkBlockedException) {
        }
        assertTrue(transport.calls.isEmpty())
    }
}
