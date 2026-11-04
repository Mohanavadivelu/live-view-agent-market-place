package dev.liveview.testbench

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.os.SystemClock
import android.util.Log
import android.widget.ArrayAdapter
import android.widget.ListView
import android.widget.TextView
import dev.liveview.testbench.data.DeviceRepository

class DevicesActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_devices)
        val status = findViewById<TextView>(R.id.devices_status)
        val list = findViewById<ListView>(R.id.devices_list)
        val repository = DeviceRepository(this)
        val started = SystemClock.elapsedRealtime()
        Log.i(TAG, "Loading the devices")
        Thread {
            repository.loadIcons()
            val devices = repository.sortedBySignal()
            runOnUiThread {
                if (isDestroyed) return@runOnUiThread
                Log.i(TAG, "Showing ${devices.size} devices after ${SystemClock.elapsedRealtime() - started} ms")
                status.text = getString(R.string.devices_count, devices.size)
                list.adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, devices.map { it.name })
                list.setOnItemClickListener { _, _, position, _ ->
                    startActivity(
                        Intent(this, DeviceDetailsActivity::class.java)
                            .putExtra(DeviceDetailsActivity.EXTRA_ID, devices[position].id)
                    )
                }
            }
        }.start()
    }

    companion object {
        private const val TAG = "Devices"
    }
}
