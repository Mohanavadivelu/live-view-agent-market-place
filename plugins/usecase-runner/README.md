# usecase-runner

Runs a plain-text use case ("disable BT / launch the pairing screen / expect …") on an Android
device through appium-mcp. It records logcat and the screen, takes a screenshot per step, checks
each `expect:` line, and leaves a run folder that log-triage (and you) can work from.

Part of the [live-view-agents](../../README.md) marketplace. **Status: S3** (`repeat:` from S4) (see
[PLAN.md](../../PLAN.md)). Installing it also installs **live-view-mcp** (the appium-mcp connection
and the device-safety rules).

```
/run-usecase usecases/testbench/02-scan.txt
```

| Kind | Name | File |
|---|---|---|
| agent | `usecase-runner` | `agents/usecase-runner.md` |
| skill | `usecase-format` | `skills/usecase-format/SKILL.md`: the plain-text format, phrases, checks, steps.json |
| skill | `run-procedure` | `skills/run-procedure/SKILL.md`: a run from start to finish |
| script | `runkit.py` | `skills/run-procedure/scripts/runkit.py`: run folder, lock, adb, timed sequences, collecting files |
| command | `/run-usecase` | `commands/run-usecase.md` |

## A use case

```
# Scanning for devices nearby
project: lv-testbench
enable BT
launch the pairing screen
tap "Scan"
wait 2 s
tap "Scan"
expect: the app stays responsive: no "isn't responding" dialog and no "ANR in" for the app in the log
expect: within 15 s the status shows "Found Pixel Buds Pro"
```

`project:` names `projects/<name>.json`: the app's package and screens, and the device.
`repeat: N` is for a use case that doesn't fail every time: `/run-usecase` runs it N times.

## The run folder

`runs/<yyyymmdd-hhmmss>-<use case>/` holds the following:

- `usecase.txt`
- `device.json`: the device, the app's version and install time, and Bluetooth, Wi-Fi and
  airplane mode before the run, which are put back after it
- `NN-<step>.png`: a screenshot per step
- `screen.mp4`
- `logcat.log`
- `crash-<n>.txt`
- `steps.json`: how each line was done, replayed by the next run of the same unchanged use case
- `result.json`: the verdict (pass, fail or blocked) and each check with its evidence

## Needs

- appium-mcp running: live-view-app → Tools → appium-mcp → Start.
- Python 3.9+ for `runkit.py`.
- adb on PATH, or `ANDROID_HOME`.

To run without permission prompts in Claude Code, allow appium-mcp's tools and the one script:

```json
"permissions": {
  "allow": [
    "mcp__plugin_live-view-mcp_appium",
    "Bash(python *runkit.py*)",
    "PowerShell(python *runkit.py*)"
  ]
}
```

## Install

```
/plugin install usecase-runner --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install usecase-runner@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
