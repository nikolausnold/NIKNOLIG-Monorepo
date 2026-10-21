package com.niknolig.app

import java.io.IOException
import java.io.ByteArrayOutputStream
import java.net.SocketTimeoutException
import java.net.URL
import javax.net.ssl.HttpsURLConnection

internal sealed class BackendHealthResult {
    data object Ready : BackendHealthResult()
    data object NotConfigured : BackendHealthResult()
    data object InvalidResponse : BackendHealthResult()
    data object TimedOut : BackendHealthResult()
    data object NetworkError : BackendHealthResult()
    data class HttpError(val statusCode: Int) : BackendHealthResult()
}

internal class BackendHealthClient(
    private val baseUrl: String,
    private val openConnection: (URL) -> HttpsURLConnection = {
        it.openConnection() as HttpsURLConnection
    },
) {
    fun check(): BackendHealthResult {
        if (baseUrl.isBlank() || !baseUrl.startsWith("https://", ignoreCase = true)) {
            return BackendHealthResult.NotConfigured
        }

        val url = runCatching {
            URL("${baseUrl.trimEnd('/')}/health/ready")
        }.getOrNull() ?: return BackendHealthResult.NotConfigured

        var connection: HttpsURLConnection? = null
        return try {
            connection = openConnection(url)
            connection.connectTimeout = TIMEOUT_MILLISECONDS
            connection.readTimeout = TIMEOUT_MILLISECONDS
            connection.requestMethod = "GET"
            connection.instanceFollowRedirects = false
            connection.useCaches = false

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
                if (READY_BODY.matches(body)) BackendHealthResult.Ready
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
        val READY_BODY = Regex("""\s*\{\s*"status"\s*:\s*"ready"\s*}\s*""")
    }
}
