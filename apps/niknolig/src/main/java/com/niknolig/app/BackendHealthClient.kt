package com.niknolig.app

import java.io.IOException
import java.io.ByteArrayOutputStream
import java.net.SocketTimeoutException
import java.net.URL
import java.net.URI
import javax.net.ssl.HttpsURLConnection

internal sealed class BackendHealthResult {
    data object Live : BackendHealthResult()
    data object Ready : BackendHealthResult()
    data object NotConfigured : BackendHealthResult()
    data object InvalidResponse : BackendHealthResult()
    data object TimedOut : BackendHealthResult()
    data object NetworkError : BackendHealthResult()
    data class HttpError(val statusCode: Int) : BackendHealthResult()
}

internal enum class BackendHealthEndpoint(val path: String, val status: String) {
    LIVE("/health/live", "live"),
    READY("/health/ready", "ready"),
}

internal class BackendHealthClient(
    private val baseUrl: String,
    private val openConnection: (URL) -> HttpsURLConnection = {
        it.openConnection() as HttpsURLConnection
    },
) {
    fun check(endpoint: BackendHealthEndpoint = BackendHealthEndpoint.READY): BackendHealthResult {
        if (baseUrl.isBlank() || !baseUrl.startsWith("https://", ignoreCase = true)) {
            return BackendHealthResult.NotConfigured
        }

        val url = runCatching {
            val origin = URI(baseUrl)
            require(origin.host != null && origin.rawUserInfo == null &&
                origin.rawQuery == null && origin.rawFragment == null &&
                origin.path in listOf("", "/") &&
                (origin.port == -1 || origin.port in 1..65535))
            origin.resolve(endpoint.path).toURL()
        }.getOrNull() ?: return BackendHealthResult.NotConfigured

        var connection: HttpsURLConnection? = null
        return try {
            connection = openConnection(url)
            connection.connectTimeout = TIMEOUT_MILLISECONDS
            connection.readTimeout = TIMEOUT_MILLISECONDS
            connection.requestMethod = "GET"
            connection.instanceFollowRedirects = false
            connection.useCaches = false
            connection.setRequestProperty("Accept", "application/json")

            val statusCode = connection.responseCode
            if (statusCode != 200) {
                BackendHealthResult.HttpError(statusCode)
            } else if (!connection.contentType.orEmpty()
                    .substringBefore(';')
                    .trim()
                    .equals("application/json", ignoreCase = true)
            ) {
                BackendHealthResult.InvalidResponse
            } else {
                val body = connection.inputStream.use { input ->
                    val output = ByteArrayOutputStream()
                    val buffer = ByteArray(1024)
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        if (output.size() + count > MAX_RESPONSE_BYTES) {
                            return BackendHealthResult.InvalidResponse
                        }
                        output.write(buffer, 0, count)
                    }
                    output.toByteArray().toString(Charsets.UTF_8)
                }
                if (ReadyResponseJsonParser(body).matches(endpoint.status)) {
                    when (endpoint) {
                        BackendHealthEndpoint.LIVE -> BackendHealthResult.Live
                        BackendHealthEndpoint.READY -> BackendHealthResult.Ready
                    }
                }
                else BackendHealthResult.InvalidResponse
            }
        } catch (_: SocketTimeoutException) {
            BackendHealthResult.TimedOut
        } catch (_: IOException) {
            BackendHealthResult.NetworkError
        } catch (_: SecurityException) {
            BackendHealthResult.NetworkError
        } finally {
            connection?.disconnect()
        }
    }

    private companion object {
        const val TIMEOUT_MILLISECONDS = 5_000
        const val MAX_RESPONSE_BYTES = 4_096
    }
}

private class ReadyResponseJsonParser(private val text: String) {
    private var position = 0

    fun matches(expectedStatus: String): Boolean = runCatching {
        skipWhitespace()
        expect('{')
        skipWhitespace()
        val key = parseString()
        skipWhitespace()
        expect(':')
        skipWhitespace()
        val value = parseString()
        skipWhitespace()
        expect('}')
        skipWhitespace()
        position == text.length && key == "status" && value == expectedStatus
    }.getOrDefault(false)

    private fun parseString(): String {
        expect('"')
        val value = StringBuilder()
        while (position < text.length) {
            val character = text[position++]
            when {
                character == '"' -> return value.toString()
                character == '\\' -> {
                    require(position < text.length)
                    when (val escape = text[position++]) {
                        '"', '\\', '/' -> value.append(escape)
                        'b' -> value.append('\b')
                        'f' -> value.append('\u000C')
                        'n' -> value.append('\n')
                        'r' -> value.append('\r')
                        't' -> value.append('\t')
                        'u' -> value.append(parseUnicodeEscape())
                        else -> error("Invalid JSON escape")
                    }
                }
                character < ' ' -> error("Unescaped control character")
                else -> value.append(character)
            }
        }
        error("Unterminated JSON string")
    }

    private fun parseUnicodeEscape(): Char {
        require(position + 4 <= text.length)
        val digits = text.substring(position, position + 4)
        require(digits.all { it in '0'..'9' || it in 'a'..'f' || it in 'A'..'F' }) {
            "Invalid JSON unicode escape"
        }
        val codeUnit = digits.toInt(16)
        position += 4
        return codeUnit.toChar()
    }

    private fun skipWhitespace() {
        while (position < text.length) {
            when (text[position]) {
                ' ', '\t', '\n', '\r' -> position++
                else -> return
            }
        }
    }

    private fun expect(character: Char) {
        require(position < text.length && text[position] == character)
        position++
    }
}
