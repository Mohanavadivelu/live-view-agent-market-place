package dev.liveview.testbench.data

import android.content.Context

class SettingsStore(context: Context) {
    private val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    fun scanTimeoutSeconds(): Int =
        parseSeconds(prefs.getString(KEY_SCAN_TIMEOUT, null) ?: DEFAULT_SCAN_TIMEOUT)

    fun autoConnect(): Boolean = prefs.getBoolean(KEY_AUTO_CONNECT, true)

    fun save(scanTimeoutSeconds: Int, autoConnect: Boolean) {
        prefs.edit()
            .putString(KEY_SCAN_TIMEOUT, "${scanTimeoutSeconds}s")
            .putBoolean(KEY_AUTO_CONNECT, autoConnect)
            .apply()
    }

    companion object {
        const val KEY_SCAN_TIMEOUT = "scan_timeout"
        const val KEY_AUTO_CONNECT = "auto_connect"
        const val DEFAULT_SCAN_TIMEOUT = "12s"

        /** A duration as stored, like "12s", in seconds. */
        fun parseSeconds(value: String): Int = value.trim().toInt()
    }
}
