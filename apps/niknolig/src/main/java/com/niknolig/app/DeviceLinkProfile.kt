package com.niknolig.app

import android.content.Context

internal object DeviceLinkProfile {
    const val APP_AREA = "niknolig"
    const val DEVICE_KEY_ALIAS = "niknolig_device_key_v1"
    const val STATE_KEY_ALIAS = "niknolig_link_state_v1"

    /** NIKNOLIG is the management side and reports no protection state of its own. */
    fun statusReport(context: Context): Pair<String, String?>? = null
}
