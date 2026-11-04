package dev.liveview.testbench.data

import android.content.Context
import android.util.Log
import java.io.File
import java.io.FileInputStream
import java.io.IOException

/** The devices paired with this phone (a fixed list: the test bench has no real ones). */
class DeviceRepository(private val context: Context) {

    fun all(): List<Device> = KNOWN_DEVICES

    fun find(id: String): Device? = KNOWN_DEVICES.firstOrNull { it.id == id }

    /** Strongest signal first. */
    fun sortedBySignal(): List<Device> =
        all().sortedWith { a, b -> signalStrength(b).compareTo(signalStrength(a)) }

    /** Measures a device's signal: one short radio query per call. */
    fun signalStrength(device: Device): Int {
        Thread.sleep(SIGNAL_QUERY_MS)
        return device.rssi
    }

    /** Each device's icon, from the icon cache. */
    fun loadIcons(): Map<String, ByteArray> {
        IconCache.ensure(context)
        val dir = File(context.filesDir.path + "icons")
        val icons = mutableMapOf<String, ByteArray>()
        for (device in all()) {
            try {
                FileInputStream(File(dir, "${device.kind}.png")).use { icons[device.id] = it.readBytes() }
            } catch (e: IOException) {
                Log.e(TAG, "Couldn't open the icon for ${device.name}", e)
            }
        }
        return icons
    }

    companion object {
        private const val TAG = "DeviceRepository"
        const val SIGNAL_QUERY_MS = 30L

        val KNOWN_DEVICES = listOf(
            Device("d01", "Pixel Buds Pro", "headphones", -48, 82),
            Device("d02", "Galaxy Watch 6", "watch", -61, 54),
            Device("d03", "JBL Flip 6", "speaker", -70, 33),
            Device("d04", "MX Keys Mini", "keyboard", -55, 90),
            Device("d05", "Car Audio", "car", -77, 100),
            Device("d06", "Sony WH-1000XM5", "headphones", -52, 67),
            Device("d07", "Pixel Watch 3", "watch", -58, 71),
            Device("d08", "Bose SoundLink", "speaker", -66, 45),
            Device("d09", "K380", "keyboard", -73, 28),
            Device("d10", "Kitchen Speaker", "speaker", -80, 100),
            Device("d11", "AirPods Pro", "headphones", -50, 59),
            Device("d12", "Fitbit Charge 6", "watch", -69, 38),
            Device("d13", "Office Keyboard", "keyboard", -63, 77),
            Device("d14", "Bike Computer", "watch", -84, 22),
            Device("d15", "Nothing Ear", "headphones", -57, 93),
            Device("d16", "Soundbar", "speaker", -62, 100),
            Device("d17", "Garmin Venu 3", "watch", -71, 64),
            Device("d18", "Car Kit", "car", -79, 100),
            Device("d19", "Jabra Elite 8", "headphones", -54, 41),
            Device("d20", "Travel Keyboard", "keyboard", -75, 12),
            Device("d21", "Marshall Emberton", "speaker", -68, 86),
            Device("d22", "Amazfit GTR", "watch", -60, 49),
            Device("d23", "Rental Car", "car", -88, 100),
            Device("d24", "Beats Studio", "headphones", -65, 75),
        )
    }
}
