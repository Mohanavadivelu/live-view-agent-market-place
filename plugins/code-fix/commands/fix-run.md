---
description: Find the root cause of a triaged run in the source, propose a fix, ask before changing any code (Gate 1), then apply it, build and run the unit tests. Nothing is pushed to the device.
argument-hint: "<run folder>"
---

Investigate and fix this run: $ARGUMENTS

If no run folder was given, take the newest folder in `runs/` that has a triage.json, and say which.

1. **Triage first.** If the run has no `triage.json`, use the log-triage agent on it.
2. **Investigate.** Use the code-investigator agent on the run folder. If it says there is nothing
   to fix in this project (the code isn't ours, or the class is environment or pass), give its
   answer and stop.
3. **Gate 1. Ask the user; never assume the answer.** Show the run's `investigation.md` as it is
   (the cause, the root cause file:line, the log lines, the diff, what will be built). Then ask,
   with AskUserQuestion if you have it, otherwise in the chat, and wait:
   - **Apply**: apply this change, build it and run the unit tests.
   - **Change**: the user says what to change.
   - **Stop**: change nothing.

   If the user can't be asked (nobody is there to answer), stop here and say that the proposal is
   waiting in the run folder.
4. **Change:** give the user's note to the code-investigator agent to revise the proposal, then ask
   Gate 1 again with the new investigation.md. **Stop:** say where the proposal is, and stop.
5. **Apply:** use the fixer agent on the run folder, and tell it that the user approved the fix.
6. **If the build or the tests failed** (the fixer undid the change), give the errors to the
   code-investigator agent for a revised proposal, and ask Gate 1 again. After two failed builds,
   stop and report.
7. **Answer** with the root cause (file:line), the change (the files), the build and the test
   results, and what comes next: build-push (Gate 2), then running the use case again. The change
   is left uncommitted.
