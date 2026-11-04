package dev.liveview.testbench

import android.app.Activity
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.ListView
import android.widget.TextView
import dev.liveview.testbench.data.NearbyScanner

class PairingActivity : Activity() {
    private var scanner: NearbyScanner? = null
    private lateinit var status: TextView
    private lateinit var nearby: ArrayAdapter<String>

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_pairing)
        status = findViewById(R.id.pairing_status)
        nearby = ArrayAdapter(this, android.R.layout.simple_list_item_1, mutableListOf())
        findViewById<ListView>(R.id.nearby_list).adapter = nearby
        findViewById<Button>(R.id.scan).setOnClickListener { scan() }
    }

    override fun onResume() {
        super.onResume()
        scanner = NearbyScanner.create(this)
        status.setText(R.string.pairing_searching)
        nearby.clear()
        scanner!!.start { device -> nearby.add(device.label) }
    }

    override fun onPause() {
        scanner?.stop()
        super.onPause()
    }

    private fun scan() {
        status.setText(R.string.pairing_searching)
        val found = scanner?.scanNow(NearbyScanner.SCAN_TIMEOUT_SECONDS)
        status.text = if (found != null) getString(R.string.pairing_found, found.name) else getString(R.string.pairing_nothing)
    }
}
