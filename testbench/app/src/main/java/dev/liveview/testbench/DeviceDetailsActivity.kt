package dev.liveview.testbench

import android.app.Activity
import android.os.Bundle
import android.widget.TextView
import dev.liveview.testbench.data.DeviceRepository
import kotlin.random.Random

class DeviceDetailsActivity : Activity() {
    private data class Details(val name: String, val kind: String, val battery: String)

    @Volatile
    private var details = Details(name = "Unknown device", kind = "—", battery = "—")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_device_details)
        val device = DeviceRepository(this).find(intent.getStringExtra(EXTRA_ID).orEmpty())
        if (device == null) {
            finish()
            return
        }
        render()
        // The name and the battery level are read from the device separately.
        Thread {
            val current = details
            Thread.sleep(Random.nextLong(QUERY_MS))
            details = current.copy(name = device.name, kind = device.kind)
            runOnUiThread { render() }
        }.start()
        Thread {
            Thread.sleep(Random.nextLong(QUERY_MS))
            details = details.copy(battery = "${device.battery} %")
            runOnUiThread { render() }
        }.start()
    }

    private fun render() {
        val shown = details
        findViewById<TextView>(R.id.device_name).text = shown.name
        findViewById<TextView>(R.id.device_kind).text = getString(R.string.details_kind, shown.kind)
        findViewById<TextView>(R.id.device_battery).text = getString(R.string.details_battery, shown.battery)
    }

    companion object {
        const val EXTRA_ID = "device_id"
        private const val QUERY_MS = 200L
    }
}
