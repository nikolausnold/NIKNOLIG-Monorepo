package org.niknolig.devicelink

/**
 * Local-network discovery announcement (Android NSD). It is only a hint that a device of the other app is
 * offering to pair: it never contains the pairing code, tokens or user data, and trust is established
 * exclusively by the backend pairing flow with mutual confirmation.
 */
data class DiscoveryAnnouncement(val area: String, val displayName: String) {
    fun txt(): Map<String, String> = mapOf("v" to "1", "area" to area, "name" to sanitizeName(displayName))

    companion object {
        const val SERVICE_TYPE = "_niknolig-pair._tcp."
        const val MAX_NAME = 40
        private const val MAX_NAME_BYTES = MAX_NAME * 4

        /** Accepts only well-formed announcements of the other app; names are stripped of control characters. */
        fun parse(txt: Map<String, ByteArray?>, ownArea: String): DiscoveryAnnouncement? {
            fun value(key: String, maxBytes: Int = 64) =
                txt[key]?.takeIf { it.size <= maxBytes }?.toString(Charsets.UTF_8)
            if (value("v") != "1") return null
            val area = value("area") ?: return null
            if (area !in PairingQr.AREAS || area == ownArea) return null
            val name = sanitizeName(value("name", MAX_NAME_BYTES) ?: return null)
            return DiscoveryAnnouncement(area, name.ifBlank { area })
        }

        fun sanitizeName(raw: String): String {
            val codePoints = raw.codePoints()
                .filter {
                    !Character.isISOControl(it) && it != 0x202E && it != 0x2066 && it != 0x2067 && it != 0x2069
                }
                .limit(MAX_NAME.toLong())
                .toArray()
            return String(codePoints, 0, codePoints.size).trim()
        }
    }
}
