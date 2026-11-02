package org.elektroengel.core

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.nio.charset.StandardCharsets
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalAnalysisServerTest {
    @Test
    fun httpRequestReturnsACompleteLocalAnalysis() {
        LocalAnalysisServer(0).use { server ->
            server.start()
            val response = post(
                server,
                "/v1/electro-engel/analyze/word-breakdown",
                "Freiheit",
            )

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains(""""engine":"deterministic-local-rules""""))
            assertTrue(response.body().contains(""""heading":"Wortbedeutung · Arbeitsfassung""""))
            assertTrue(response.body().contains("Handlungsspielraum oder Selbstbestimmung"))
            assertTrue(response.body().contains(""""sourceStatus":"NOT_CHECKED""""))
            assertTrue(response.body().contains(""""sources":[]}"""))
        }
    }

    @Test
    fun httpRequestRejectsBlankOversizedAndInvalidUtf8Input() {
        LocalAnalysisServer(0).use { server ->
            server.start()
            val blank = post(server, "/v1/electro-engel/analyze/fact-check", " \n ")
            assertEquals(400, blank.statusCode())
            assertTrue(blank.body().contains(""""code":"EMPTY_INPUT""""))

            val oversized = post(
                server,
                "/v1/electro-engel/analyze/fact-check",
                "x".repeat(2049),
            )
            assertEquals(400, oversized.statusCode())
            assertTrue(oversized.body().contains(""""code":"VALIDATION_FAILED""""))

            val invalidUtf8 = HttpRequest.newBuilder(
                URI("http://127.0.0.1:${server.port}/v1/electro-engel/analyze/fact-check"),
            )
                .header("Content-Type", "text/plain; charset=utf-8")
                .POST(HttpRequest.BodyPublishers.ofByteArray(byteArrayOf(0xc3.toByte(), 0x28)))
                .build()
            val invalidResponse = HttpClient.newHttpClient().send(
                invalidUtf8,
                HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8),
            )
            assertEquals(400, invalidResponse.statusCode())
            assertTrue(invalidResponse.body().contains(""""code":"VALIDATION_FAILED""""))
        }
    }

    @Test
    fun httpRequestRejectsUnknownRoutesAndWrongContentTypes() {
        LocalAnalysisServer(0).use { server ->
            server.start()
            val unknown = post(server, "/v1/electro-engel/analyze/nope", "Freiheit")
            assertEquals(404, unknown.statusCode())
            assertTrue(unknown.body().contains(""""code":"NOT_FOUND""""))

            val wrongType = HttpRequest.newBuilder(
                URI("http://127.0.0.1:${server.port}/v1/electro-engel/analyze/fact-check"),
            )
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString("Freiheit"))
                .build()
            val invalidResponse = HttpClient.newHttpClient().send(
                wrongType,
                HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8),
            )
            assertEquals(400, invalidResponse.statusCode())
            assertTrue(invalidResponse.body().contains(""""code":"VALIDATION_FAILED""""))
        }
    }

    private fun post(
        server: LocalAnalysisServer,
        path: String,
        text: String,
    ): HttpResponse<String> {
        val request = HttpRequest.newBuilder(URI("http://127.0.0.1:${server.port}$path"))
            .header("Content-Type", "text/plain; charset=utf-8")
            .POST(HttpRequest.BodyPublishers.ofString(text, StandardCharsets.UTF_8))
            .build()
        return HttpClient.newHttpClient().send(
            request,
            HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8),
        )
    }
}
