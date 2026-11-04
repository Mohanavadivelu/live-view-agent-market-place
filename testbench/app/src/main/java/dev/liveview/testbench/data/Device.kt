package dev.liveview.testbench.data

data class Device(
    val id: String,
    val name: String,
    val kind: String,
    val rssi: Int,
    val battery: Int,
)
