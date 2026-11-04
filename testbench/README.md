# LV Test Bench

A small Android app (Kotlin, framework Views, minSdk 30, no libraries) with bugs planted in it, the
target the agents are proven on: the use cases in [usecases/testbench/](../usecases/testbench/), the
project config in [projects/lv-testbench.json](../projects/lv-testbench.json).

Screens: Home (Bluetooth on or off, three buttons), Pairing (devices nearby, Scan), My devices
(24 paired devices, strongest signal first), a device's details (name, kind, battery), and Settings
(scan timeout, connect automatically). Pairing, My devices and Settings can be started directly:
`am start -n dev.liveview.testbench/.PairingActivity`.

Where the bugs are is in `eval/answers/` and nowhere in this folder. Agents being evaluated
mustn't read it.

## Build and install

Needs the Android SDK (`ANDROID_HOME`) and a JDK 17 or later (`JAVA_HOME`; Android Studio's
`jbr` will do).

```powershell
cd testbench
.\gradlew.bat :app:assembleDebug            # app\build\outputs\apk\debug\app-debug.apk
.\gradlew.bat :app:testDebugUnitTest        # the unit tests
```

The data push, as `projects/lv-testbench.json` describes it:

```powershell
adb -s emulator-5554 push app\build\outputs\apk\debug\app-debug.apk /data/local/tmp/lv-testbench.apk
adb -s emulator-5554 shell pm install -r -t /data/local/tmp/lv-testbench.apk
adb -s emulator-5554 shell am force-stop dev.liveview.testbench
```

## After a fix run

`.\reset-bugs.ps1` puts the planted bugs back: the sources as committed, and nothing a fixer added.
Then build and install again.
