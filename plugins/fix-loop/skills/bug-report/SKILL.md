---
name: bug-report
description: How to write bug-report.md, the bug report for a use case run, from its run folder (result.json, triage.json, signals.json, screenshots). It covers the title, the summary table, the steps to reproduce, expected and actual, the evidence, the reproduction rate and the other findings, for a failed run and for a passing one. Use when a run has been triaged and someone needs the report, or to file the failure as a bug.
---

# The bug report

`bug-report.md` goes into the run folder that log-triage triaged. (Not `report.md`: Claude Code
doesn't let a subagent write files called report.md or summary.md.) It is written for someone who
wasn't there: a developer picking up the bug, or a tester filing it. It must make sense without
the other files, and point to them for the detail.

Write it from the files only: `usecase.txt`, `device.json`, `result.json`, `triage.json` (and
`triage.md`), `signals.json` and the screenshots. Don't add causes or fixes that triage didn't find.
If something is missing (no triage.json, no logcat.log), say so in the report and write what the
rest shows.

## A failed run

```markdown
# <What is wrong, in the user's words>

<One or two sentences: what the user does, what happens, how often.>

| | |
|---|---|
| Use case | `usecases/…/01-pairing-bt-off.txt`: <its title> |
| Result | fail in <k> of <n> runs |
| Class | crash · our code (`dev.liveview.testbench`) |
| Device | sdk_gphone64_x86_64, Android 17 (API 37), user build, emulator-5554 |
| App | dev.liveview.testbench 1.0, installed <app_updated> |
| Run | `runs/<run>/` (<date and time>) |

## Steps to reproduce

1. Disable Bluetooth.
2. Launch the pairing screen.

The use case's action lines, as numbered steps in plain words.

## Expected

<The expect lines that failed, in plain words.>

## Actual

<What was seen: the screen text, the dialog, the crash, the time measured.>

## Evidence

<The signature, then 10–20 log lines, fenced, with their line numbers in logcat.log.>

- [03-tap-pair-a-device.png](03-tap-pair-a-device.png): <what it shows>
- [crash-1.txt](crash-1.txt): <what it is>
- [screen.mp4](screen.mp4): the whole run
- [triage.md](triage.md): the triage

## Other findings

<From triage.json's other_findings, one line each. Leave the section out when there are none.>
```

- **The title** says what the user sees ("The app crashes when the pairing screen opens with
  Bluetooth off"), not the class or the exception.
- **Result:** the reproduction rate from triage.json's `repro`. If the use case asks for `repeat:
  N` and fewer runs were made, say so.
- **Class:** the class and whose code: "our code (package)", "not ours: <process>" or "owner
  unknown".
- **Links** are relative to the run folder, so the report works when the folder is copied or
  attached.
- Keep it to what a developer needs to reproduce and recognise the bug. The full detail stays in
  triage.md and the run's files.

## A passing run

```markdown
# Passed: <use case title>

| | |
|---|---|
| Use case | … |
| Result | pass in <k> of <n> runs |
| Device | … |
| App | … |
| Run | … |

<Each check with what was seen, one line each.>

## Other findings
```

## When it is done

Answer with the title, the result line, the class line and the path of bug-report.md.
