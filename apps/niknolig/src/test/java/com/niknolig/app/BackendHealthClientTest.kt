package com.niknolig.app

import java.io.ByteArrayInputStream
import java.io.InputStream
import java.net.URL
import java.security.cert.Certificate
import javax.net.ssl.HttpsURLConnection
import org.junit.Assert.assertEquals
import org.junit.Test

class BackendHealthClientTest {
    @Test
    fun enforcesTheExactResponseByteLimitForEachHealthRoute() {
        for (endpoint in BackendHealthEndpoint.entries) {
            val json = """{"status":"${endpoint.status}"}"""
            val atLimit = " ".repeat(4096 - json.length) + json
            val expected = if (endpoint == BackendHealthEndpoint.LIVE) {
                BackendHealthResult.Live
            } else BackendHealthResult.Ready
            for ((body, result) in listOf(
                atLimit to expected, (" " + atLimit) to BackendHealthResult.InvalidResponse,
            )) {
                assertEquals(
                    result,
                    BackendHealthClient("https://api.example.test") {
                        FakeHttpsConnection(it, 200, body)
                    }.check(endpoint),
                )
            }
        }
    }

    @Test
    fun livenessUsesItsOwnRouteAndCannotEstablishReadiness() {
        var requestedUrl: URL? = null
        val client = BackendHealthClient("https://api.niknolig.com/") {
            requestedUrl = it
            FakeHttpsConnection(it, 200, """{"status":"live"}""")
        }
        assertEquals(BackendHealthResult.Live, client.check(BackendHealthEndpoint.LIVE))
        assertEquals("https://api.niknolig.com/health/live", requestedUrl.toString())
        assertEquals(BackendHealthResult.InvalidResponse, client.check())
        assertEquals(
            BackendHealthResult.InvalidResponse,
            BackendHealthClient("https://api.niknolig.com") {
                FakeHttpsConnection(it, 200, """{"status":"ready"}""")
            }.check(BackendHealthEndpoint.LIVE),
        )
    }

    @Test
    fun rejectsNonOriginUrlsBeforeAnyRequest() {
        for (value in listOf(
            "https://user:password@api.example.test", "https://api.example.test/prefix",
            "https://api.example.test?query", "https://api.example.test#fragment",
            "https:///health", "https://api.example.test:65536",
        )) {
            var opened = false
            val result = BackendHealthClient(value) {
                opened = true
                FakeHttpsConnection(it, 200, """{"status":"ready"}""")
            }.check()
            assertEquals(value, BackendHealthResult.NotConfigured, result)
            assertEquals(value, false, opened)
        }
    }

    @Test
    fun rejectsWrongContentTypeForBothEndpoints() {
        for (endpoint in BackendHealthEndpoint.entries) {
            val connection = FakeHttpsConnection(
                URL("https://api.example.test"), 200,
                """{"status":"${endpoint.status}"}""", "text/html",
            )
            assertEquals(
                BackendHealthResult.InvalidResponse,
                BackendHealthClient("https://api.example.test") { connection }.check(endpoint),
            )
            assertEquals(true, connection.disconnected)
        }
    }

    @Test
    fun requestsOnlyTheReadinessRouteOverHttpsAndAcceptsTheContractResponse() {
        var requestedUrl: URL? = null
        val connection = FakeHttpsConnection(URL("https://api.example.test/health/ready"), 200, """{"status":"ready"}""")

        val result = BackendHealthClient("https://api.example.test") {
            requestedUrl = it
            connection
        }.check()

        assertEquals(BackendHealthResult.Ready, result)
        assertEquals("https://api.example.test/health/ready", requestedUrl.toString())
        assertEquals("GET", connection.requestMethod)
        assertEquals(5_000, connection.connectTimeout)
        assertEquals(5_000, connection.readTimeout)
        assertEquals(false, connection.instanceFollowRedirects)
        assertEquals(false, connection.useCaches)
        assertEquals("application/json", connection.getRequestProperty("Accept"))
        assertEquals(null, connection.getRequestProperty("Authorization"))
        assertEquals(null, connection.getRequestProperty("Cookie"))
        assertEquals(true, connection.disconnected)
    }

    @Test
    fun rejectsUnconfiguredAndNonHttpsEndpointsWithoutOpeningConnection() {
        var opened = false
        val factory: (URL) -> HttpsURLConnection = {
            opened = true
            FakeHttpsConnection(it, 200, """{"status":"ready"}""")
        }

        assertEquals(BackendHealthResult.NotConfigured, BackendHealthClient("").check())
        assertEquals(
            BackendHealthResult.NotConfigured,
            BackendHealthClient("http://api.example.test", factory).check(),
        )
        assertEquals(false, opened)
    }

    @Test
    fun rejectsUnexpectedResponsesAndSurfacesOnlyTheHttpStatus() {
        val invalid = BackendHealthClient("https://api.example.test") {
            FakeHttpsConnection(it, 200, """{"status":"live"}""")
        }.check()
        val legacyHealth = BackendHealthClient("https://api.example.test") {
            FakeHttpsConnection(
                it, 200, """{"status":"ok","service":"NOLD API","version":"0.2.0"}""",
            )
        }.check()
        val unauthorized = BackendHealthClient("https://api.example.test") {
            FakeHttpsConnection(it, 401, """{"error":{"code":"AUTHENTICATION_REQUIRED"}}""")
        }.check()

        assertEquals(BackendHealthResult.InvalidResponse, invalid)
        assertEquals(BackendHealthResult.InvalidResponse, legacyHealth)
        assertEquals(BackendHealthResult.HttpError(401), unauthorized)
    }

    @Test
    fun parsesEscapedJsonStringsAndRejectsInvalidWhitespaceAndTrailingContent() {
        val escaped = BackendHealthClient("https://api.example.test") {
            FakeHttpsConnection(it, 200, """{"status":"re\u0061dy"}""")
        }.check()
        val signedEscape = BackendHealthClient("https://api.example.test") {
            FakeHttpsConnection(it, 200, """{"status":"re\u+061dy"}""")
        }.check()
        val verticalTab = BackendHealthClient("https://api.example.test") {
            FakeHttpsConnection(it, 200, "\u000B{\"status\":\"ready\"}")
        }.check()
        val extraProperty = BackendHealthClient("https://api.example.test") {
            FakeHttpsConnection(it, 200, """{"status":"ready","extra":true}""")
        }.check()
        val trailingContent = BackendHealthClient("https://api.example.test") {
            FakeHttpsConnection(it, 200, """{"status":"ready"} false""")
        }.check()

        assertEquals(BackendHealthResult.Ready, escaped)
        assertEquals(BackendHealthResult.InvalidResponse, signedEscape)
        assertEquals(BackendHealthResult.InvalidResponse, verticalTab)
        assertEquals(BackendHealthResult.InvalidResponse, extraProperty)
        assertEquals(BackendHealthResult.InvalidResponse, trailingContent)
    }

    @Test
    fun reportsReadinessFailureAndRejectsRedirectsAndOversizedBodies() {
        for (status in listOf(302, 503)) {
            val result = BackendHealthClient("https://api.example.test") {
                FakeHttpsConnection(it, status, """{"status":"ready"}""")
            }.check()
            assertEquals(BackendHealthResult.HttpError(status), result)
        }
        val connection = FakeHttpsConnection(
            URL("https://api.example.test/health/ready"), 200,
            " ".repeat(4096) + """{"status":"ready"}""",
        )
        assertEquals(
            BackendHealthResult.InvalidResponse,
            BackendHealthClient("https://api.example.test") { connection }.check(),
        )
        assertEquals(true, connection.disconnected)
    }

    @Test
    fun distinguishesTimeoutFromNetworkAndTlsFailureWithoutReturningReady() {
        assertEquals(
            BackendHealthResult.TimedOut,
            BackendHealthClient("https://api.example.test") {
                throw java.net.SocketTimeoutException()
            }.check(),
        )
        for (error in listOf(java.io.IOException(), javax.net.ssl.SSLHandshakeException("untrusted"))) {
            assertEquals(
                BackendHealthResult.NetworkError,
                BackendHealthClient("https://api.example.test") { throw error }.check(),
            )
        }
    }

    private class FakeHttpsConnection(
        url: URL,
        private val status: Int,
        private val body: String,
        private val responseContentType: String = "application/json; charset=utf-8",
    ) : HttpsURLConnection(url) {
        var disconnected = false

        override fun connect() = Unit
        override fun disconnect() {
            disconnected = true
        }
        override fun usingProxy() = false
        override fun getCipherSuite() = "TLS_TEST"
        override fun getLocalCertificates(): Array<Certificate>? = null
        override fun getServerCertificates(): Array<Certificate> = emptyArray()
        override fun getResponseCode() = status
        override fun getContentType() = responseContentType
        override fun getInputStream(): InputStream = ByteArrayInputStream(body.toByteArray())
    }
}
