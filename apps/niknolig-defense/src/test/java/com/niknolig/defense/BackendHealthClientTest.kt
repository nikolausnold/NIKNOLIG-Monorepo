package com.niknolig.defense

import java.io.ByteArrayInputStream
import java.io.InputStream
import java.net.URL
import java.security.cert.Certificate
import javax.net.ssl.HttpsURLConnection
import org.junit.Assert.assertEquals
import org.junit.Test

class BackendHealthClientTest {
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
        override fun getContentType() = "application/json; charset=utf-8"
        override fun getInputStream(): InputStream = ByteArrayInputStream(body.toByteArray())
    }
}
