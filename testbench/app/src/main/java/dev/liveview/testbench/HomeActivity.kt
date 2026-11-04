package dev.liveview.testbench

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import dev.liveview.testbench.data.BluetoothState

class HomeActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)
        findViewById<Button>(R.id.open_pairing).setOnClickListener { open(PairingActivity::class.java) }
        findViewById<Button>(R.id.open_devices).setOnClickListener { open(DevicesActivity::class.java) }
        findViewById<Button>(R.id.open_settings).setOnClickListener { open(SettingsActivity::class.java) }
    }

    override fun onResume() {
        super.onResume()
        findViewById<TextView>(R.id.bluetooth_status).setText(
            if (BluetoothState.isOn(this)) R.string.home_bluetooth_on else R.string.home_bluetooth_off
        )
    }

    private fun open(screen: Class<out Activity>) {
        startActivity(Intent(this, screen))
    }
}
