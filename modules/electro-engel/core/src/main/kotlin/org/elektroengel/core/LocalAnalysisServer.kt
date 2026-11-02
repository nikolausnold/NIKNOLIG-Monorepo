package org.elektroengel.core

import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpServer
import java.io.IOException
import java.net.InetSocketAddress
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors

private const val MAX_REQUEST_BYTES = 2048
private const val ANALYZE_PATH = "/v1/electro-engel/analyze/"

class LocalAnalysisServer(port: Int) : AutoCloseable {
    private val executor = Executors.newFixedThreadPool(4)
    private val server = HttpServer.create(InetSocketAddress("127.0.0.1", port), 16).apply {
        setExecutor(this@LocalAnalysisServer.executor)
        createContext("/") { exchange -> handle(exchange) }
    }

    val port: Int
        get() = server.address.port

    fun start() {
        server.start()
        logEvent("server_started", null, null, null, null)
    }

    override fun close() {
        server.stop(0)
        executor.shutdownNow()
    }

    private fun handle(exchange: HttpExchange) {
        val requestId = UUID.randomUUID().toString()
        val response = try {
            process(exchange, requestId)
        } catch (_: Exception) {
            Response(
                status = 500,
                body = errorJson("INTERNAL_ERROR", requestId),
                mode = null,
                outcome = "error",
            )
        }

        logEvent("request_completed", requestId, response.mode, response.status, response.outcome)
        try {
            exchange.responseHeaders.set("Content-Type", "application/json; charset=utf-8")
            exchange.responseHeaders.set("Cache-Control", "no-store")
            exchange.responseHeaders.set("X-Content-Type-Options", "nosniff")
            if (response.status == 405) exchange.responseHeaders.set("Allow", "POST")
            val bytes = response.body.toByteArray(StandardCharsets.UTF_8)
            exchange.sendResponseHeaders(response.status, bytes.size.toLong())
            exchange.responseBody.use { it.write(bytes) }
        } catch (_: IOException) {
            exchange.close()
        } finally {
            exchange.close()
        }
    }

    private fun process(exchange: HttpExchange, requestId: String): Response {
        if (exchange.requestMethod != "POST") {
            return Response(405, errorJson("METHOD_NOT_ALLOWED", requestId), null, "rejected")
        }
        if (exchange.requestURI.rawQuery != null) {
            return Response(400, errorJson("VALIDATION_FAILED", requestId), null, "rejected")
        }

        val mode = parseMode(exchange.requestURI.rawPath)
            ?: return Response(404, errorJson("NOT_FOUND", requestId), null, "rejected")
        val contentTypes = exchange.requestHeaders["Content-type"].orEmpty()
        if (contentTypes.size != 1 ||
            !Regex("""(?i)^text/plain(?:;\s*charset=utf-8)?$""")
                .matches(contentTypes.single().trim())
        ) {
            return Response(400, errorJson("VALIDATION_FAILED", requestId), mode, "rejected")
        }

        val contentLengths = exchange.requestHeaders["Content-length"].orEmpty()
        if (contentLengths.size > 1) {
            return Response(400, errorJson("VALIDATION_FAILED", requestId), mode, "rejected")
        }
        val declaredLength = contentLengths.singleOrNull()?.toLongOrNull()
        if (contentLengths.isNotEmpty() &&
            (declaredLength == null || declaredLength < 0 || declaredLength > MAX_REQUEST_BYTES)
        ) {
            return Response(400, errorJson("VALIDATION_FAILED", requestId), mode, "rejected")
        }

        val bytes = exchange.requestBody.use { it.readNBytes(MAX_REQUEST_BYTES + 1) }
        if (bytes.size > MAX_REQUEST_BYTES ||
            (declaredLength != null && bytes.size.toLong() != declaredLength)
        ) {
            return Response(400, errorJson("VALIDATION_FAILED", requestId), mode, "rejected")
        }
        val text = try {
            StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(bytes))
                .toString()
        } catch (_: Exception) {
            return Response(400, errorJson("VALIDATION_FAILED", requestId), mode, "rejected")
        }

        return when (val outcome = ElectroEngelAnalyzer.analyze(AnalysisRequest(mode, text))) {
            is AnalysisOutcome.Success -> Response(
                status = 200,
                body = successJson(requestId, outcome.result),
                mode = mode,
                outcome = "success",
            )
            is AnalysisOutcome.Failure -> Response(
                status = 400,
                body = errorJson(outcome.reason.name, requestId),
                mode = mode,
                outcome = "rejected",
            )
        }
    }

    private fun parseMode(path: String): AnalysisMode? {
        if (!path.startsWith(ANALYZE_PATH)) return null
        return when (path.removePrefix(ANALYZE_PATH)) {
            "word-breakdown" -> AnalysisMode.WORD_BREAKDOWN
            "convention-scan" -> AnalysisMode.CONVENTION_SCAN
            "perspective-shift" -> AnalysisMode.PERSPECTIVE_SHIFT
            "fact-check" -> AnalysisMode.FACT_CHECK
            else -> null
        }
    }

    private data class Response(
        val status: Int,
        val body: String,
        val mode: AnalysisMode?,
        val outcome: String,
    )
}

private fun successJson(requestId: String, result: AnalysisResult): String =
    buildString {
        append("""{"requestId":${jsonString(requestId)},"engine":"deterministic-local-rules"""")
        append(""","mode":${jsonString(result.mode.name.lowercase().replace('_', '-'))}""")
        append(""","sections":[""")
        append(result.sections.joinToString(",") { section ->
            """{"heading":${jsonString(section.heading)},"content":${jsonString(section.content)}}"""
        })
        append("""]""")
        append(""","uncertainty":${jsonString(result.uncertainty)}""")
        append(""","sourceStatus":${jsonString(result.sourceStatus.name)},"sources":[]}""")
    }

private fun errorJson(code: String, requestId: String): String =
    """{"error":{"code":${jsonString(code)},"message":"Analysis request could not be completed.","requestId":${jsonString(requestId)}}}"""

private fun jsonString(value: String): String = buildString {
    append('"')
    value.forEach { char ->
        when (char) {
            '"' -> append("\\\"")
            '\\' -> append("\\\\")
            '\b' -> append("\\b")
            '\u000c' -> append("\\f")
            '\n' -> append("\\n")
            '\r' -> append("\\r")
            '\t' -> append("\\t")
            in '\u0000'..'\u001f' -> {
                append("\\u")
                append(char.code.toString(16).padStart(4, '0'))
            }
            else -> append(char)
        }
    }
    append('"')
}

private fun logEvent(
    event: String,
    requestId: String?,
    mode: AnalysisMode?,
    status: Int?,
    outcome: String?,
) {
    val fields = mutableListOf(""""event":${jsonString(event)}""")
    if (requestId != null) fields += """"requestId":${jsonString(requestId)}"""
    if (mode != null) fields += """"mode":${jsonString(mode.name.lowercase())}"""
    if (status != null) fields += """"status":$status"""
    if (outcome != null) fields += """"outcome":${jsonString(outcome)}"""
    println("{${fields.joinToString(",")}}")
}

fun main() {
    val port = (System.getenv("ELECTRO_ENGEL_PORT") ?: "8081").toIntOrNull()
        ?.takeIf { it in 1..65535 }
        ?: throw IllegalArgumentException("ELECTRO_ENGEL_PORT must be between 1 and 65535")
    val server = LocalAnalysisServer(port)
    val stopped = CountDownLatch(1)
    Runtime.getRuntime().addShutdownHook(Thread {
        server.close()
        stopped.countDown()
    })
    server.start()
    stopped.await()
}
