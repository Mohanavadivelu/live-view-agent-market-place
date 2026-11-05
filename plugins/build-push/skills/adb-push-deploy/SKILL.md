---
name: adb-push-deploy
description: How built files get onto an Android device and back off it. It covers the push plan, what Gate 2 shows and its three answers, backups, adb root, remount and disable-verity, push, mode, owner and SELinux context, sha256 checks on the device, restarts, waiting for the device to come back, and rollback. Uses the pushkit.py helper. Use when planning, approving, doing or undoing an adb push.
---

# Pushing to a device

Nothing is pushed until the user has seen the plan and said yes: **Gate 2**. This is a separate yes
from Gate 1. A yes to changing the code isn't a yes to pushing it.

```
python "${CLAUDE_SKILL_DIR}/scripts/pushkit.py" <command> <run folder>
```

Run it from the workspace root, one plain call at a time. Don't run adb yourself for any of this:
pushkit does the checks that make it safe to undo.

| Command | Does |
|---|---|
| `plan [--project NAME] [--serial S]` | reads the device, changes nothing. Writes `push-plan.json` and `push-plan.md` |
| `push [--reboot]` | exactly what the plan shows, and writes `push-result.json`. A failed step or check puts the backup back by itself |
| `status` | what is on the device now, against the backup and the pushed files |
| `rollback [--force]` | puts the backup back and checks it. `--force` is for files that changed since the push |

`push` refuses if the built files, the project config or the device aren't the ones in the plan.

## Gate 2 (asked by whoever talks to the user)

Show `push-plan.md` as it is, and ask, with three answers:

- **Push**: do what the plan says.
- **Push and reboot**: the same, but reboot the device instead of the plan's restart.
- **Stop**: nothing is pushed. The built files and any fix stay as they are.

Never assume a yes: not from Gate 1, an earlier push or a previous run. If no one can be asked, stop
at the gate. A subagent can't ask the user, so the gate is asked by the command that runs the agents.

If the plan shows unit tests that failed, say so when you ask.

## What push does

**Data mode:**

1. Back up the files in `/data/local/tmp/` that will be replaced, and the installed app's APKs.
2. `adb push`, then the sha256 on the device against the built file's.
3. `push.install`, then `push.restart`.
4. Check that the package manager's APK is the built one.

**System mode:**

1. `adb root`, then `adb remount`. The first time on a device, this needs `adb disable-verity` and
   a reboot. Gate 2 says so.
2. Back up every file that will be replaced: the file, sha256, mode, owner and SELinux context.
3. `adb push` each file, then its mode and owner. A replaced file keeps its old context, and a new
   one gets `restorecon`. Then the sha256 on the device.
4. `push.restart` (`stop; start`) or a reboot. Wait until apps can really run: `sys.boot_completed`
   is 1, the package manager answers, the activity manager says `mBooted=true`, `/sdcard` is back
   and the user is unlocked. After `stop; start`, system_server must also be a new process.
   `sys.boot_completed` stays 1 through a framework restart, and the package manager answers about
   15 s before `/sdcard` does. A device with a PIN stays locked until a person unlocks it, so the
   wait for that ends after 60 s without a rollback: say that it needs unlocking.
5. If a pushed file is an APK of the app, check that the package manager has it.

The backup is `runs/<run>/backup/` with `manifest.json`, as the device-safety skill says. A second
push from the same run keeps the first backup, so a rollback goes back to the original.

## Rollback

Ask first, unless it is the automatic one after a failed push: Gate 2's text promises that one. Show
`pushkit status <run>`, say what will happen, and wait for a yes.

- A file that existed is restored. A file that didn't is deleted, along with the folder the push
  made for it if that is now empty.
- In data mode the backed-up app is reinstalled (`adb install -r -d -t`), which keeps its data. If the
  app wasn't installed before, it is uninstalled, **which deletes its data**: say so.
- After a good rollback the backup is deleted, since everything in it is back on the device.
- If a file changed on the device since the push, rollback refuses. Tell the user what changed, and
  use `--force` only if they say so.

## When something fails

Report `push-result.json`: `error`, `checks`, `steps`, and `rolled_back`. If the rollback failed too,
or the device doesn't come back, **stop and say so plainly**: the device needs a person. Don't try
other commands on it. Never wipe it or reflash it (device-safety).

Common failures:

| What it says | Why | What to do |
|---|---|---|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | the installed app has another signature | Ask the user. Uninstalling it would delete its data |
| `INSTALL_FAILED_VERSION_DOWNGRADE` | the build's version is lower than the installed one | Tell the user. The build's version needs raising |
| `adbd cannot run as root` or `ro.debuggable=0` | a user or Google Play build | System push can't work here. Use another device or data mode |
| `the device didn't come back` | the pushed code stops the boot | pushkit restores the backup if adb still reaches the device. Otherwise a person must look at it |
