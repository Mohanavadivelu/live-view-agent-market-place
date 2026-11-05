---
description: Put back what a run pushed to the device, from the run's backup, after showing what will change and asking first.
argument-hint: "<run folder>"
---

Roll back this run's push: $ARGUMENTS

If no run folder was given, take the newest folder in `runs/` that has a backup/manifest.json, and say which.

1. **Look.** Use the pusher agent on the run folder for its **Status**. If there is no backup, say
   so and stop.
2. **Ask the user; never assume the answer.** Say what will happen to each file (restored or
   deleted), whether the app is reinstalled or uninstalled (uninstalling deletes its data), and any
   file that changed since the push. Ask with AskUserQuestion if you have it, otherwise in the chat:
   **Roll back** or **Stop**. If the user can't be asked, stop here.
3. **Roll back:** use the pusher agent on the run folder, and tell it that the user approved the
   rollback. If files changed since the push, tell it `--force` only if the user said so.
4. **Answer** with what was restored, the checks, and whether the device came back.
