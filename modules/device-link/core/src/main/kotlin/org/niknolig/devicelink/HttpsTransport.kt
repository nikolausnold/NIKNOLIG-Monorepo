package org.niknolig.devicelink

import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.URL
import javax.net.ssl.HttpsURLConnection

/** HTTPS-only JSON transport: no redirects, no cleartext, bounded timeouts and response size. */
class HttpsTransport(
    baseUrl: String,
    private val timeoutMillis: Int = 8_000,
    private val openConnection: (URL) -> HttpsURLConnection = { it.openConnection() as HttpsURLConnection },
) : DeviceLinkTransport {
    private val origin = baseUrl.trim().trimEnd('/')

    init {
        require(origin.startsWith("https://", ignoreCase = true)) { "Backend URL must use HTTPS" }
    }

    override fun request(method: String, path: String, bearer: String?, body: Map<String, Any?>?): TransportResponse {
        require(path.startsWith("/v1/")) { "Unexpected path" }
        var connection: HttpsURLConnection? = null
        try {
            connection = openConnection(URL(origin + path))
            connection.connectTimeout = timeoutMillis
            connection.readTimeout = timeoutMillis
            connection.requestMethod = method
            connection.instanceFollowRedirects = false
            connection.useCaches = false
            connection.setRequestProperty("Accept", "application/json")
            if (bearer != null) connection.setRequestProperty("Authorization", "Bearer $bearer")
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(Json.encode(body).toByteArray(Charsets.UTF_8)) }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.use { readBounded(it) }.orEmpty()
            val parsed = if (text.isBlank()) emptyMap() else runCatching { Json.decodeObject(text) }
                .getOrElse { throw DeviceLinkProtocolException(status, "body") }
            return TransportResponse(status, parsed)
        } catch (error: SocketTimeoutException) {
            throw DeviceLinkNetworkException(true, error)
        } catch (error: IOException) {
            throw DeviceLinkNetworkException(false, error)
        } finally {
            connection?.disconnect()
        }
    }

    private fun readBounded(input: java.io.InputStream): String {
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(2048)
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            if (output.size() + count > MAX_RESPONSE_BYTES) throw DeviceLinkProtocolException(0, "body")
            output.write(buffer, 0, count)
        }
        return output.toString(Charsets.UTF_8.name())
    }

    private companion object {
        const val MAX_RESPONSE_BYTES = 65_536
    }
}
