---
description: Triage a use case run folder: what failed, the class of failure, whose code it is and the evidence (writes triage.md and triage.json)
argument-hint: "<run folder or use case file>"
---

Use the log-triage agent on this run: $ARGUMENTS

If nothing was given, take the newest folder in `runs/`.

When it is done, give its answer as it is: the class, whose code, the summary, the reproduction
rate and the path of triage.md.
