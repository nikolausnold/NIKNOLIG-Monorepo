package org.niknolig.devicelink

/**
 * Local-network discovery announcement (Android NSD). It is only a hint that a device of the other app is
 * offering to pair: it never contains the pairing code, tokens or user data, and trust is established
 * exclusively by the backend pairing flow with mutual confirmation.
 */
data class DiscoveryAnnouncement(val area: String, val displayName: String) {
    fun txt(): Map<String, String> = mapOf("v" to "1", "area" to area, "name" to displayName.take(MAX_NAME))

    companion object {
        const val SERVICE_TYPE = "_niknolig-pair._tcp."
        const val MAX_NAME = 40

        /** Accepts only well-formed announcements of the other app; names are stripped of control characters. */
        fun parse(txt: Map<String, ByteArray?>, ownArea: String): DiscoveryAnnouncement? {
            fun value(key: String) = txt[key]?.takeIf { it.size <= 64 }?.toString(Charsets.UTF_8)
            if (value("v") != "1") return null
            val area = value("area") ?: return null
            if (area !in PairingQr.AREAS || area == ownArea) return null
            val name = sanitizeName(value("name") ?: return null)
            return DiscoveryAnnouncement(area, name.ifBlank { area })
        }

        fun sanitizeName(raw: String): String =
            raw.filter { !it.isISOControl() && it != '\u202E' && it != '\u2066' && it != '\u2067' && it != '\u2069' }
                .trim().take(MAX_NAME)
    }
}
