---
name: run-procedure
description: How a use case run is done, from start to finish. It covers the run folder, the device lock, noting and restoring the device's state, recording logcat and the screen, a screenshot per step, the checks, and result.json, using the runkit.py helper. Use whenever a use case is run on an Android device, whether first run or replay.
---

# Running a use case

The steps are in **usecase-format**, and the device rules are in live-view-mcp's **device-safety**.
A run is **unattended**: don't stop to ask unless the run can't go on (no device, appium-mcp
missing, a step that would break device-safety). Run the use case **once**: never repeat it to get
a different outcome. Repeating is the verifier's job.

## runkit

The mechanical parts are one script, so that they work the same every time and need one
permission:

```
python "${CLAUDE_SKILL_DIR}/scripts/runkit.py" <command> …
```

Run it from the workspace root, one call per command. Don't chain it with `&&` or `;`, and don't
put variables in front: a plain call is what permission rules match. It prints JSON (`adb` prints
adb's output).

| Command | Does |
|---|---|
| `start <usecase.txt> [--serial S]` | creates `runs/<time>-<name>/` with `usecase.txt` and `device.json`, takes the device's lock, and finds the project and an earlier `steps.json` to replay. It prints all of this |
| `adb <serial> <args…>` | adb for anything appium-mcp's safe mode refuses (`shell cmd …`, `shell pm clear …`). adb doesn't need to be on PATH, and device paths survive Git Bash |
| `seq <serial> "tap X Y" "wait 2" …` | a timed sequence in one adb call, timed on the device (see usecase-format). It prints each item's device time |
| `wait <seconds>` | waits on the host |
| `collect <run> <file> [<name>]` | copies a file into the run folder: screenshots, the screen recording, logcat, crash reports. **appium-mcp saves its files outside the workspace: always bring them in with collect**, not with cp or Copy-Item |
| `restore <run>` | puts Bluetooth, Wi-Fi and airplane mode back as `device.json` has them |
| `finish <run>` | lists the run files still missing and releases the lock |

## 1. Prepare

1. `runkit start <use case>` (with `--serial` if the user named a device). If it says the device is
   locked, stop and pass that on. Keep what it printed: `run`, `serial`, `package`, `screens`,
   `mode`, `replay_from`.
2. `select_device` with the serial.
3. **Session.** `appium_session_management` `list`, and use an open session on this device. Else
   `create` one with its `udid`. Remember whether you created it.
4. **Recordings.** `adb_logcat` `start_recording` with `clear_first: true`, then
   `appium_screen_recording` `start` with `time_limit_seconds` 600. Note the time: "since the run
   started" counts from here. Every `since_seconds` is the time since then, never more, and anything
   logged or recorded before it belongs to an earlier run.
5. **A known start.** `adb_app` `force_stop` the project's app, so nothing from an earlier run
   (an open screen, a dialog) is still there.
6. For a **replay**, read `replay_from`.

## 2. The steps

For each line, in order:

- **Action:** do it (interpret, or replay the recorded actions), then `appium_screenshot` and
  `runkit collect` it as `NN-<short-name>.png` (NN = the line's step number).
- **Timed sequences** (taps, keys and waits in a row) run as one `runkit seq` call, so the waits are
  exact. Take their screenshots afterwards.
- A **`wait N s`** on its own counts from when the previous action was sent, and its screenshot
  time is part of it. So wait only for the rest.
- **Check:** do it, and note pass or fail, the evidence and the time.
- Note each step's start and end time (host clock).
- **Replay:** if a recorded action fails (element not found, a different screen), interpret that
  line instead, mark the step `"reinterpreted": true`, and go on replaying.
- **A step that fails** (it can't be done, or the app crashed): keep the screenshot and the error,
  and stop the steps. A failed **check** doesn't stop the run.
- Look at every screenshot. An error dialog or a crash with no expect line about it still goes
  into `unexpected`.

## 3. Finish (always, after a failure too)

1. `appium_screen_recording` `stop`, then `runkit collect` the .mp4 as `screen.mp4`.
2. `adb_logcat` `stop_recording`, then `runkit collect` its file as `logcat.log`.
3. `adb_crashes` `list` since the start. For each crash or ANR, `get` it and `runkit collect` the
   saved report as `crash-<n>.txt`.
4. `runkit restore <run>`. Delete the Appium session only if you created it.
5. **steps.json**: the run as it was done (format in usecase-format), with `usecase_sha256` from
   start. For a replay, write the replayed steps with the reinterpreted ones updated.
6. **result.json:**

   ```json
   {
     "usecase": "usecases/testbench/02-scan.txt",
     "verdict": "fail",
     "mode": "interpret",
     "started": "2026-11-04T09:00:20+05:30", "ended": "2026-11-04T09:00:58+05:30",
     "device": "emulator-5554",
     "steps": [
       {"n": 4, "line": "tap \"Scan\"", "status": "done", "start": "…", "end": "…", "screenshot": "04-tap-scan.png"},
       {"n": 8, "line": "expect: …no \"ANR in\"…", "status": "fail", "evidence": "ANR in dev.liveview.testbench (Input dispatching timed out) at 09:00:27"}
     ],
     "unexpected": [],
     "files": ["usecase.txt", "device.json", "steps.json", "logcat.log", "screen.mp4", "crash-1.txt"]
   }
   ```

   - `verdict`: **pass** if every check passed and nothing unexpected happened. **fail** if a
     check failed or the app crashed. **blocked** if the run couldn't be done: the device, Appium,
     or a step that isn't possible.
   - `steps[].status`: done, failed, pass, fail or skipped.
7. `runkit finish <run>`. If it lists missing files, say so in result.json's `unexpected` (rewrite
   the file) and in your answer.

## 4. The answer

Give the verdict, a line per check (✔ / ✘ and its evidence), anything unexpected, and the run
folder. Don't explain causes or suggest fixes: that is log-triage's work, which starts from this
folder.
