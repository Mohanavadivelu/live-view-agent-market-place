package dev.liveview.testbench.data

import android.content.Context
import java.io.File

/** One icon per kind of device, kept in the app's files (written on first use). */
object IconCache {
    val KINDS = listOf("headphones", "watch", "speaker", "keyboard", "car")

    fun ensure(context: Context) {
        val dir = File(context.filesDir, "icons")
        if (!dir.isDirectory) dir.mkdirs()
        for (kind in KINDS) {
            val file = File(dir, "$kind.png")
            if (!file.exists()) file.writeBytes(kind.toByteArray())
        }
    }
}
