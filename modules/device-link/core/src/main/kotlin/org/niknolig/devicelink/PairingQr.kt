package org.niknolig.devicelink

import java.net.URI

/** QR payload carrying a one-time pairing code. The code expires after 120 s and is single-use server-side. */
data class PairingQr(val code: String, val area: String) {
    fun encode(): String = "$SCHEME://$HOST?v=1&area=$area&code=$code"

    companion object {
        const val SCHEME = "niknolig-pair"
        private const val HOST = "pair"
        const val CODE_LENGTH = 8
        const val CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        val AREAS = setOf("niknolig", "niknolig-defense")

        /** Same normalisation as the backend: strips spaces and dashes, upper-cases, validates alphabet. */
        fun normalizeCode(value: String): String? {
            val code = value.replace("-", "").replace(" ", "").uppercase()
            return code.takeIf { it.length == CODE_LENGTH && it.all { c -> c in CODE_ALPHABET } }
        }

        /** Returns null for anything that is not a well-formed payload from the other NIKNOLIG app. */
        fun parse(text: String, ownArea: String): PairingQr? {
            if (text.length > 200) return null
            val uri = runCatching { URI(text) }.getOrNull() ?: return null
            if (uri.scheme != SCHEME || uri.host != HOST || uri.rawFragment != null || uri.rawUserInfo != null) return null
            val params = (uri.rawQuery ?: return null).split('&').associate {
                val parts = it.split('=', limit = 2)
                if (parts.size != 2) return null
                parts[0] to parts[1]
            }
            if (params.keys != setOf("v", "area", "code") || params["v"] != "1") return null
            val area = params["area"]!!
            // Only the other app can pair with this one; same-area codes would be rejected by the backend anyway.
            if (area !in AREAS || area == ownArea) return null
            val code = normalizeCode(params["code"]!!) ?: return null
            return PairingQr(code, area)
        }
    }
}
