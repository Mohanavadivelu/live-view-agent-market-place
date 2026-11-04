---
description: Run a plain-text use case on the Android device and leave a run folder (logcat, screen recording, screenshots, steps.json, result.json)
argument-hint: "<use case file> [device serial]"
---

Use the usecase-runner agent to run this use case: $ARGUMENTS

If no file was given, list the `.txt` files under `usecases/` and ask which one.

If the use case has a `repeat: N` line, run the agent N times, one run after another (each leaves
its own run folder), and give a line per run.

When it is done, give its answer as it is: the verdict, the checks, anything unexpected and the run
folder.
