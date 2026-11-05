# build-push

Builds a project and shows you exactly what would go to the device (**Gate 2**). After your yes, it
backs up what is there, adb pushes the build, checks its checksum on the device, restarts it and
waits for it to come back. If a step fails, it puts the backup back by itself, and `/rollback-run`
does the same when you ask.

Part of the [live-view-agents](../../README.md) marketplace. **Status: S6** (see
[PLAN.md](../../PLAN.md)). Installing it also installs live-view-mcp.

```
/push-run runs/20261104-095033-04-settings
/rollback-run runs/20261104-095033-04-settings
```

| Kind | Name | File |
|---|---|---|
| command | `/push-run` | `commands/push-run.md`: build, plan, Gate 2, push |
| command | `/rollback-run` | `commands/rollback-run.md`: status, ask, roll back |
| agent | `builder` | `agents/builder.md`: builds and writes the plan; changes nothing on the device |
| agent | `pusher` | `agents/pusher.md`: carries out an approved push or rollback |
| skill | `project-config` | `skills/project-config/SKILL.md`: `projects/<name>.json`, data and system mode, a new project |
| skill | `build-module` | `skills/build-module/SKILL.md`: the build and its files |
| skill | `adb-push-deploy` | `skills/adb-push-deploy/SKILL.md`: the plan, Gate 2, the push, rollback, failures |
| script | `buildkit.py` | `skills/build-module/scripts/buildkit.py`: `build` |
| script | `pushkit.py` | `skills/adb-push-deploy/scripts/pushkit.py`: `plan`, `push`, `status`, `rollback` |

## Gate 2

The builder writes `push-plan.md`: the device, the build and test results, each file → device path
with its sha256 and what is there now, the backup, and the restart. `/push-run` shows it and asks:

- **Push**: do what the plan says.
- **Push and reboot**: the same, but reboot instead of the plan's restart.
- **Stop**: nothing is pushed.

A yes at Gate 1 doesn't count here. `push` refuses if the built files, the project config or the
device aren't the ones in the plan, if the latest build failed, or if another run holds the device.

## The two modes

| | Data | System |
|---|---|---|
| For | an app you can install | anything in the system image |
| Device | any | `adb root` must work: userdebug, eng, or a **Google APIs** emulator started with `-writable-system` |
| Rollback | reinstalls the old app and keeps its data | restores the files with their mode, owner and SELinux context |

To set up a system-push emulator: install a Google APIs image (not Google Play), create an emulator
from it and start it with `emulator -avd <name> -writable-system`. The first push runs
`adb disable-verity` and reboots it, as Gate 2 says.

## What a push doesn't show

It shows that the files arrived and that the device came back, not that the bug is gone. Run the use
case again (`/run-usecase`), or use the whole loop (fix-loop).

A device with a PIN stays locked after a reboot until a person unlocks it. pushkit waits 60 s for
that, then treats the device as up without rolling back. Tested only on devices with no PIN.

## The run folder, after a push

`artifacts.json`, `build.log`, `push-plan.md`, `push-plan.json`, `backup/` (with `manifest.json`) and
`push-result.json`. A good rollback deletes `backup/`, since everything in it is back on the device.

## Needs

- A project config (`projects/<name>.json`) with `build` and `push`. See the project-config skill,
  `projects/schema.json` and `projects/example-aosp.json`.
- Python 3.9+, adb (on PATH or through `ANDROID_HOME`), and what the project's build needs.

To run without permission prompts in Claude Code (Gate 2 still asks):

```json
"permissions": {
  "allow": [
    "Bash(python *buildkit.py*)",
    "PowerShell(python *buildkit.py*)",
    "Bash(python *pushkit.py*)",
    "PowerShell(python *pushkit.py*)"
  ]
}
```

## Install

```
/plugin install build-push --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install build-push@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
