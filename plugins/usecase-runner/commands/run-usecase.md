---
description: Run a plain-text use case on the Android device and leave a run folder (logcat, screen recording, screenshots, steps.json, result.json)
argument-hint: "<use case file> [device serial]"
---

Use the usecase-runner agent to run this use case: $ARGUMENTS

If no file was given, list the `.txt` files under `usecases/` and ask which one.

When it is done, give its answer as it is: the verdict, the checks, anything unexpected and the run
folder.
