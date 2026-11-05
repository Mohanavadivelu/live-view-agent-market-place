---
name: project-config
description: The project config file (projects/<name>.json) that tells the agents how to find, build and push a project's code. It covers source roots, tests, the app, the owner, the build command, data and system push, restarts and the device, and how to write one for a new project. Use when setting up a new project, or when a build or a push asks for a config or complains about one.
---

# The project config

Each project has one file, `projects/<name>.json`, with `name` the same as the file's name. Use
cases name it with a line `project: <name>`. `projects/schema.json` is the full list of fields, and
`python scripts/validate.py` checks every config against it.

```json
{
  "name": "notes",
  "description": "The notes app",
  "source_roots": ["notes/app/src/main"],
  "tests": "notes/app/src/test",
  "app": {
    "package": "com.example.notes",
    "launch": "com.example.notes/.MainActivity",
    "screens": {"editor": "com.example.notes/.EditorActivity"}
  },
  "build": {
    "cwd": "notes",
    "command": "gradlew.bat :app:assembleDebug",
    "test": "gradlew.bat :app:testDebugUnitTest",
    "env": {"JAVA_HOME": "C:/Program Files/Android/Android Studio/jbr"}
  },
  "push": {
    "mode": "data",
    "files": [{"local": "notes/app/build/outputs/apk/debug/app-debug.apk",
               "device": "/data/local/tmp/notes.apk"}],
    "install": "pm install -r -t /data/local/tmp/notes.apk",
    "restart": "am force-stop com.example.notes"
  },
  "device": {"serial": "emulator-5554"}
}
```

| Field | What |
|---|---|
| `source_roots`, `tests` | the folders the agents may read and change, from the workspace root. Nothing outside them is changed |
| `app` | the package, and what "launch the app" and "launch the <name> screen" open |
| `owner` | what counts as our code in a log, when that is more than the app's package |
| `build.command`, `build.test` | what makes the pushed files, and what runs the unit tests. `cwd`, `env` and `timeout_s` (default 1800) apply to both |
| `push.files` | each built file (`local`, from the workspace root) and where it goes (`device`). In system mode also `mode` and `owner` |
| `push.install`, `push.restart` | shell commands on the device, after the push. `push.reboot: true` reboots instead, and `push.boot_timeout_s` is how long to wait for the device to come back (default 300) |
| `device.serial` | the device. Without it, the one connected device. With several connected, name it |

## Which push mode

| | `data` | `system` |
|---|---|---|
| For | an app you can install | anything in the system image: a system app, a framework jar, a native library |
| Device | any, a user build too | **`adb root` must work**: a userdebug or eng build, or an emulator with a Google APIs image started with `-writable-system` (not a Google Play image) |
| Files go to | `/data/local/tmp/`, then `install` installs them | their real path, such as `/system/app/Notes/Notes.apk` |
| Restart | `am force-stop <package>` | `stop; start` (the framework), or `reboot: true` |
| A rollback | reinstalls the app that was there, keeping its data | restores the files, with their mode, owner and SELinux context |

`projects/example-aosp.json` is an example for an AOSP tree.

**Commands the config can't ask for:** the device-safety rules apply to `install` and `restart` too,
so a config that wipes, flashes or reboots into the bootloader or recovery is refused.

## A new project

Ask the user for what can't be found out: the source folder, the build command and the built files'
paths. Read `build.gradle` or `Android.bp` for the rest. Write the config, run `validate.py`, and
try the build with build-module before anything is pushed.
