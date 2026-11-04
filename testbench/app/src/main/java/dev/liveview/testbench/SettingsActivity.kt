package dev.liveview.testbench

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.Switch
import android.widget.Toast
import dev.liveview.testbench.data.SettingsStore

class SettingsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)
        val store = SettingsStore(this)
        val timeout = findViewById<EditText>(R.id.scan_timeout)
        val autoConnect = findViewById<Switch>(R.id.auto_connect)
        try {
            timeout.setText(store.scanTimeoutSeconds().toString())
            autoConnect.isChecked = store.autoConnect()
        } catch (e: RuntimeException) {
            Log.e(TAG, "Couldn't load the settings", e)
            AlertDialog.Builder(this)
                .setTitle(R.string.settings_error_title)
                .setMessage(getString(R.string.settings_error_message, e.javaClass.simpleName))
                .setPositiveButton(android.R.string.ok, null)
                .show()
        }
        findViewById<Button>(R.id.save_settings).setOnClickListener {
            val seconds = timeout.text.toString().toIntOrNull() ?: return@setOnClickListener
            store.save(seconds, autoConnect.isChecked)
            Toast.makeText(this, R.string.settings_saved, Toast.LENGTH_SHORT).show()
        }
    }

    companion object {
        private const val TAG = "Settings"
    }
}
