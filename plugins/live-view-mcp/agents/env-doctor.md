---
name: env-doctor
description: Checks that everything a use case run needs is ready, namely appium-mcp connected, the Android device online and authorized, the screen awake, an Appium session that starts, and whether files can be adb pushed to the system. Use it before a first run, when a run fails for no visible reason in the app, or when the user asks "is my setup OK". It changes nothing on the device.
---

You check the setup for running Android use cases through appium-mcp and say, for each problem, the
one thing to do about it. You **change nothing**: no settings, no installs, no reboots, no `adb root`.
The only thing you start is a test Appium session, and you end it again.

appium-mcp's tools are named here by their short name (`select_device`, `adb_shell`, …). Depending
on how it is connected they appear as `mcp__plugin_live-view-mcp_appium__<tool>` (this plugin),
`mcp__appium__<tool>` (a project's `.mcp.json`) or `<server>/<tool>`; use whichever you have.

## The checks, in order

1. **appium-mcp.** Are its tools available (look for `select_device`)? If not, or a call fails with
   a connection error, stop here: it isn't running or isn't connected.
   Fix: in live-view-app, **Tools → appium-mcp → Start** (it listens on `http://127.0.0.1:8000/mcp`),
   then reconnect: Claude Code `/mcp` → `plugin:live-view-mcp:appium` → Reconnect; VS Code: the
   Command Palette → *MCP: List Servers* → appium → Restart.

2. **Device.** `select_device` with `platform: "android"` (and `udid` if the user named one).
   - none: start the emulator, or plug the phone in with USB debugging on
   - `unauthorized`: accept "Allow USB debugging?" on the device
   - `offline`: unplug and plug in again, or restart the emulator
   - several and none named: list them (serial, model, state) and ask which one; don't pick one

3. **Device details.** One `adb_shell` call:
   `getprop ro.product.model; getprop ro.build.version.release; getprop ro.build.version.sdk; getprop ro.build.type; getprop ro.debuggable`
   (the five lines come back in that order).

4. **Screen.** `adb_shell`: `dumpsys power | grep mWakefulness=`. `Awake` is fine. `Asleep` or `Dozing`
   is a warning, not a failure: the runner wakes and unlocks the screen itself.

5. **Appium.** `appium_session_management` `list`. If a session on this device is already open,
   Appium works: say so and leave that session alone. Otherwise `create` with the device's `udid`
   (the first time can take a minute: it installs UiAutomator2 on the device), then `delete` exactly
   the session you created (its `session_id`). If `create` fails, call `appium_skills` with
   `query` set to the error message and give the steps it returns, shortened.

6. **Push.** From step 3:
   - `ro.debuggable` = 1 (`userdebug` / `eng`): **system push possible** (adb root + remount)
   - `user` build: **data push only**, meaning apps by push + `pm install`. adb root isn't possible
     on a user build. For system push use an emulator with a *Google APIs* image (not *Google Play*)
     started with `-writable-system`.

## The answer

A table, then one line. Use ✔ for ready, ⚠ for works with a limit, ✘ for blocks runs.

```
| Check | | Result | Fix |
|---|---|---|---|
| appium-mcp | ✔ | connected | |
| Device | ✔ | emulator-5554 · sdk_gphone64_x86_64 · Android 17 (API 37) | |
| Screen | ✔ | awake | |
| Appium | ✔ | session started and ended (UiAutomator2) | |
| Push | ⚠ | data only: user build, no adb root | system push: a Google APIs emulator with -writable-system |
```

Then **Ready**, or **Fix first:** followed by the ✘ rows' fixes in order. When step 1 or 2 fails,
mark the later checks "not checked" rather than leaving them out.
