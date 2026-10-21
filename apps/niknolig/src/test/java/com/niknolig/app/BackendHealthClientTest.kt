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
        val unauthorized = BackendHealthClient("https://api.example.test") {
            FakeHttpsConnection(it, 401, """{"error":{"code":"AUTHENTICATION_REQUIRED"}}""")
        }.check()

        assertEquals(BackendHealthResult.InvalidResponse, invalid)
        assertEquals(BackendHealthResult.HttpError(401), unauthorized)
    }

    @Test
    fun parsesEscapedJsonStringsAndRejectsInvalidWhitespaceAndTrailingContent() {
        val escaped = BackendHealthClient("https://api.example.test") {
            FakeHttpsConnection(it, 200, """{"status":"re\u0061dy"}""")
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
        assertEquals(BackendHealthResult.InvalidResponse, verticalTab)
        assertEquals(BackendHealthResult.InvalidResponse, extraProperty)
        assertEquals(BackendHealthResult.InvalidResponse, trailingContent)
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
