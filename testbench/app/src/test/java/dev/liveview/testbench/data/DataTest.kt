package dev.liveview.testbench.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DataTest {
    @Test
    fun parsesPlainSeconds() {
        assertEquals(20, SettingsStore.parseSeconds("20"))
        assertEquals(5, SettingsStore.parseSeconds(" 5 "))
    }

    @Test
    fun deviceIdsAreUnique() {
        val ids = DeviceRepository.KNOWN_DEVICES.map { it.id }
        assertEquals(ids.size, ids.toSet().size)
    }

    @Test
    fun everyDeviceKindHasAnIcon() {
        assertTrue(DeviceRepository.KNOWN_DEVICES.all { it.kind in IconCache.KINDS })
    }
}
