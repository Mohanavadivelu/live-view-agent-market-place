---
name: usecase-format
description: The plain-text use case format (a line per step, with expect lines for the checks), how common phrases such as "disable BT", "launch the pairing screen" or "tap Scan" are done on an Android device through appium-mcp and adb, and the steps.json format that records a run for replay. Use when reading, writing or running a use case.
---

# Use cases

A use case is a plain-text file, a line per step, run top to bottom:

```
# Scanning for devices nearby
project: lv-testbench
enable BT
launch the pairing screen
tap "Scan"
expect: within 15 s the status shows "Found Pixel Buds Pro"
```

- `#` starts a comment. The first comment is the use case's title.
- `project: <name>` (optional) names `projects/<name>.json`. It gives the app's package, its
  screens, how to build and push, and the device. Without it, use the project the user named, or
  the only file in `projects/`. If there is none, ask once for the app's package.
- `expect: …` is a check, made at that point of the run. Everything else is an action.
- Quoted text is shown on screen as it is written, though case may differ ("Scan" matches a SCAN
  button).
- One line is one step. An unclear line is done the most likely way, and steps.json records how.

## Actions

The tools are appium-mcp's, named here by their short names (see live-view-mcp). **runkit adb**
is adb through the run-procedure skill's `runkit.py adb <serial> …`, for what appium-mcp's safe
mode refuses.

| Phrase | How |
|---|---|
| enable / disable BT (Bluetooth) | runkit adb `shell cmd bluetooth_manager enable` / `disable`, then check `settings get global bluetooth_on` (`adb_shell`) every second until it is 1 / 0 (up to 10 s) |
| enable / disable Wi-Fi | runkit adb `shell cmd wifi set-wifi-enabled enabled` / `disabled` |
| airplane mode on / off | runkit adb `shell cmd connectivity airplane-mode enable` / `disable` |
| launch <app> | a cold start: `adb_app` `force_stop`, then `adb_app` `start` with the project's `app.package` (and `activity` = its `app.launch`), so it opens on its first screen, not where an earlier run left it |
| launch the <name> screen | `adb_app` `force_stop`, then `adb_app` `start` with `activity` = the project's `app.screens.<name>` (the part after `/`). Without one, launch the app and go there through its UI |
| tap "<text>" | find the element in the page source (below) and tap its center with `adb_shell` `input tap X Y`. Record its resource id, text and center |
| tap <description> | the same, for the element that fits best ("the first device", "the switch") |
| type "<text>" into <field> | `appium_set_value` |
| go back / press back | `adb_shell` `input keyevent KEYCODE_BACK` |
| press home | `adb_shell` `input keyevent KEYCODE_HOME` |
| scroll to "<text>" | `appium_gesture` `scroll_to_element` |
| rotate to landscape / portrait | `appium_orientation` |
| wait N s | runkit `wait N` (see run-procedure for how it counts) |
| wait until <condition> | check the condition every second, up to 30 s (or the time the line gives) |
| clear the app's data | runkit adb `shell pm clear <package>`, for the project's own app only |
| force stop the app | `adb_app` `force_stop` |

Anything else: do what the line says with the tools that fit, and record it.

**Taps go through `input tap`, the way a person taps.** Appium waits until the app is idle before
its own actions, and so does `appium_get_page_source`. A person doesn't wait, and a tap while the
app is frozen is exactly what causes an ANR. So:

- Read the page source after anything that can change the screen (launch, tap, back, typing).
- After only a `wait`, use the last page source: reading it again would wait for the app.
- Send the tap with `input tap` (`adb_shell`). It returns at once.

**Timed sequences.** Each tool call takes seconds, so `tap "Scan"` / `wait 2 s` / `tap "Scan"`
done one call at a time puts 8 s between the taps, not 2. Lines in a row that are only taps,
swipes, key presses and `wait N s` are one **sequence**:

1. Read the page source once and work out every tap's center. In a sequence, all the elements are
   on the screen it starts from.
2. Do them in one call: `runkit seq <serial> "tap 178 457" "wait 2" "tap 178 457"`. Items are
   `tap X Y`, `swipe X1 Y1 X2 Y2 [ms]`, `key NAME` (BACK, HOME, ENTER…) and `wait S`. The device
   does the timing, and the output gives each item's device time.
3. Take the screenshots after the sequence. Each of its steps gets the same screenshot, or one per
   step if the line says to look at something in between (then it isn't a sequence).

An `expect:` line ends a sequence. So does anything that needs the screen read again, such as
tapping an element that only appears after the previous tap.

## Checks (`expect:`)

Every check ends as **pass** or **fail**, with its evidence: the text seen, the log line, the time
measured.

| Check | How |
|---|---|
| shows "<text>" / the title is "<text>" | the page source contains it (case-sensitive, so a typo fails). Put what it showed instead in the evidence |
| within N s <screen condition> | check every 0.5 s from the previous step's end. Pass if it holds by N s. Record the time it took, or "not after N s" |
| no error dialog | no dialog in the page source (`android:id/alertTitle`, "isn't responding", "keeps stopping", "has stopped") |
| the app is still running / doesn't crash | `adb_crashes` `list` for the package since the run started (java and native) is empty, and the package's process is alive (`adb_shell` `pidof <package>`) |
| no ANR / stays responsive | `adb_crashes` `list` `crash_type=anr` since the start is empty, and no `ANR in <package>` in the log. **On some devices no ANR dialog shows**, so the log is the evidence, not the screen |
| no errors from the app in the log | `adb_logcat` `get` `package=<package>` `level=E` since the run started has no lines (count them, and keep the first) |
| a value ("the battery shows 82 %") | read it (`appium_get_text` or the page source) and compare |

Something the app logs can be the better measure. For example, `Showing 24 devices after 5316 ms`
gives a time more exactly than polling the screen. Use it when it is there and say so.

## steps.json: a run as it was done

Written into the run folder. A rerun of the same use case replays it instead of working each line
out again.

```json
{
  "usecase": "usecases/testbench/02-scan.txt",
  "usecase_sha256": "…",
  "project": "lv-testbench",
  "device": {"serial": "emulator-5554", "model": "sdk_gphone64_x86_64", "android": "17", "sdk": 37},
  "steps": [
    {"n": 1, "line": "enable BT",
     "actions": [{"runkit_adb": "shell cmd bluetooth_manager enable"},
                 {"tool": "adb_shell", "args": {"command": "settings get global bluetooth_on"}, "until": "1"}]},
    {"n": 2, "line": "launch the pairing screen",
     "actions": [{"tool": "adb_app", "args": {"action": "start", "package": "dev.liveview.testbench", "activity": ".PairingActivity"}}]},
    {"n": 3, "line": "tap \"Scan\"",
     "actions": [{"tap": {"id": "dev.liveview.testbench:id/scan", "text": "SCAN", "x": 178, "y": 457}}]},
    {"n": 6, "line": "expect: within 15 s the status shows \"Found Pixel Buds Pro\"",
     "check": {"kind": "screen-text", "text": "Found Pixel Buds Pro", "within_s": 15,
               "strategy": "id", "selector": "dev.liveview.testbench:id/pairing_status"}}
  ]
}
```

- `actions`: what was called, with the arguments that worked. Use `{"tool": …, "args": …}` for
  appium-mcp, `{"runkit_adb": "<arguments after the serial>"}` for runkit adb,
  `{"wait": N}`, and `{"tap": {"id", "text", "x", "y"}}` for a tap.
- A sequence is one entry for all its lines: `{"n": [4, 5, 6], "lines": […], "seq": [{"tap":
  {"id": …, "text": …, "x": 178, "y": 457}}, {"wait": 2}, {"tap": {…}}]}`. A replay finds the
  elements again from one page source, then runs it with `runkit seq`.
- `check`: how the check was made, so that a replay checks the same thing in the same way.
- A replayed tap finds the element by `id` (else `text`) in the page source and taps its center
  now. `x`/`y` are used only when the screen hasn't changed since the last page source, as after a
  wait.
- The results (pass or fail, times, evidence) go in `result.json`, not here. steps.json says only
  how to do the run.
