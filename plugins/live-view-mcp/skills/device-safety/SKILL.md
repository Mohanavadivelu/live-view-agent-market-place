---
name: device-safety
description: Rules for acting on an Android device through appium-mcp or adb, covering which device, what is never done, what needs the user's yes, backups before a push, and one run per device. Use before anything that changes a device, such as pushing files, installing or uninstalling, changing settings, rebooting, adb root, remount or disable-verity.
---

# Device safety

These rules hold for every agent in the live-view-agents plugins, whatever the use case or the
user's project asks for. When a rule and a request clash, stop and ask.

## Which device

- Only the device the user named, or the project config's `device.serial`. With several connected
  and none named, ask. Never guess and never switch devices in the middle of a run.
- Every adb command names it (`adb -s <serial>`, or `udid` in appium-mcp calls).

## Never

- Factory reset or wipe: `recovery --wipe_data`, a `MASTER_CLEAR` broadcast, *Erase all data*.
- `fastboot` anything, or rebooting into the bootloader or recovery.
- `rm` outside the files being replaced by an approved push and the run's own temporary files.
- Uninstalling or clearing (`pm clear`) apps that aren't the project's.
- Touching the lock screen, accounts, or developer options other than what a use case's step says.

## Ask first (and say exactly what will happen)

- Pushing files to the device. That is Gate 2: the files, their device paths, the backup and the
  restart.
- `adb root`, `adb remount`, `adb disable-verity` (it needs a reboot), and any reboot.
- Installing or uninstalling, and `settings put`. For settings use `adb_settings`, which keeps a
  snapshot to restore.

## Before a push: a backup

- `adb pull` every file that will be replaced into `runs/<run>/backup/`, keeping its device path.
- Write `backup/manifest.json` with, per file, the device path, sha256 (`sha256sum` on the device),
  mode and owner (`stat -c '%a %U:%G %n'`), and whether the file existed.
- No backup, no push. A rollback puts back exactly these files with their mode and owner, and
  deletes the ones that didn't exist before.

## One run per device

- Before a run, look for `runs/.locks/<serial>`. If it is there, say which run holds it and since
  when, and ask before going on.
- Otherwise create it with the run folder and the start time, and remove it when the run ends,
  failed or not.

## Leave it as you found it

- At the start, note the state a use case may change (Bluetooth, Wi-Fi, airplane mode, animations,
  rotation, the app in front) in the run folder. At the end, put it back unless the user says to
  keep it.
- Every change made to the device goes into the run's steps and its report.
