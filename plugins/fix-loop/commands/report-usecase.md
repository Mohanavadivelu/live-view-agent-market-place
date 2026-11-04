---
description: Run a use case on the Android device, triage what broke and write a bug report (bug-report.md). No code is changed.
argument-hint: "<use case file or run folder> [device serial]"
---

Run, triage and report: $ARGUMENTS

1. **Run.** If a use case file was given, use the usecase-runner agent to run it (with the device
   serial, if one was given). If the use case has a `repeat: N` line, run it N times, one run after
   another. Each run leaves a run folder. If a run folder (`runs/…`) was given instead, skip this
   step and use that folder. If nothing was given, list the `.txt` files under `usecases/` and ask
   which one.
2. **Triage.** Use the log-triage agent on the newest run folder. It compares that run with the
   other runs of the same use case, so run them all first.
3. **Report.** Use the reporter agent on the same run folder. It writes `bug-report.md` there.
4. **Answer** with the report's title, the result (pass or fail in k of n runs), the class and whose
   code it is, and the path of bug-report.md. Don't add causes or fixes of your own.

If a run is blocked (no device, appium-mcp not running), stop there and say what to fix.
