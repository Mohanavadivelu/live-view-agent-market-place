package dev.liveview.testbench.data

import android.content.Context
import android.os.Handler
import android.os.Looper
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

data class NearbyDevice(val name: String, val rssi: Int) {
    val label: String get() = "$name  ($rssi dBm)"
}

/** Finds devices nearby (simulated: the test bench has no real ones). */
class NearbyScanner private constructor() {
    private val main = Handler(Looper.getMainLooper())
    private val fullScan = LinkedBlockingQueue<NearbyDevice>()

    @Volatile
    private var running = false

    /** Reports devices as they show up, until [stop]. */
    fun start(onFound: (NearbyDevice) -> Unit) {
        running = true
        Thread {
            for (device in NEARBY) {
                Thread.sleep(DISCOVERY_STEP_MS)
                if (!running) return@Thread
                main.post { onFound(device) }
            }
        }.start()
    }

    fun stop() {
        running = false
    }

    /** A full scan: waits for its strongest device, or null after [timeoutSeconds]. */
    fun scanNow(timeoutSeconds: Long): NearbyDevice? {
        fullScan.clear()
        Thread {
            Thread.sleep(FULL_SCAN_MS)
            fullScan.put(NEARBY.maxBy { it.rssi })
        }.start()
        return fullScan.poll(timeoutSeconds, TimeUnit.SECONDS)
    }

    companion object {
        const val SCAN_TIMEOUT_SECONDS = 12L
        private const val FULL_SCAN_MS = 10_000L
        private const val DISCOVERY_STEP_MS = 800L

        private val NEARBY = listOf(
            NearbyDevice("Pixel Buds Pro", -48),
            NearbyDevice("Living Room TV", -63),
            NearbyDevice("JBL Go 3", -71),
            NearbyDevice("Unknown device", -86),
        )

        /** A scanner, or null when the phone has no Bluetooth or it is off. */
        fun create(context: Context): NearbyScanner? {
            val adapter = BluetoothState.adapter(context) ?: return null
            if (!adapter.isEnabled) return null
            return NearbyScanner()
        }
    }
}
