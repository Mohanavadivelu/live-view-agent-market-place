---
description: Build a run's project, show the push plan, ask before touching the device (Gate 2), then adb push it with a backup, checksums and a restart. A failed check rolls it back.
argument-hint: "<run folder> [project <name>] [device <serial>]"
---

Build and push this run: $ARGUMENTS

If no run folder was given, take the newest folder in `runs/` that has a fix-result.json, and say which.

1. **Prepare.** Use the builder agent on the run folder, with the project and the device if they were
   given. If the build or the plan fails, give its answer and stop.
2. **Gate 2. Ask the user; never assume the answer.** A yes at Gate 1 doesn't count. Show the run's
   `push-plan.md` as it is. Then ask, with AskUserQuestion if you have it, otherwise in the chat,
   and wait:
   - **Push**: do what the plan says.
   - **Push and reboot**: the same, but reboot the device instead of the plan's restart.
   - **Stop**: nothing is pushed.

   If the user can't be asked (nobody is there to answer), stop here and say that the plan is
   waiting in the run folder.
3. **Stop:** say that nothing was pushed, and where the plan is.
4. **Push:** use the pusher agent on the run folder, and tell it what the user approved.
5. **Answer** with what is on the device now, the checks, and whether anything was rolled back. A push
   doesn't show that the bug is gone: what comes next is running the use case again, and
   `/rollback-run` puts the original back.
