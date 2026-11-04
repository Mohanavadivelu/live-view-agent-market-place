---
name: logcat-triage
description: How to triage an Android run from its files. It covers crash, ANR, native-crash and error signatures in logcat, which process and package own them, the time window around the failed step, comparing repeated runs (flaky), the failure classes, and the triage.md and triage.json it writes. Use when a use case run (a runs/<run> folder) failed, or passed with something odd, and the question is what broke and whose code it is.
---

# Triage a run

A run folder (`runs/<time>-<use case>/`, from usecase-runner) holds `usecase.txt`, `device.json`,
`result.json`, `logcat.log` (threadtime: main, system, crash), `screen.mp4`, a screenshot per
step and `crash-<n>.txt`. Triage answers four questions from them:

1. **What failed:** the step, and what was seen instead.
2. **What kind of failure:** the class (below).
3. **Whose code:** the app's (ours), the platform's or another app's, or unknown.
4. **The evidence:** log lines, crash files and screenshots, so that someone else can check it.

Triage reads files. It doesn't touch the device, change code or explain how to fix it: that is
code-fix's work (stage S5), which starts from triage.json.

## triagekit

```
python "${CLAUDE_SKILL_DIR}/scripts/triagekit.py" scan <run folder>
python "${CLAUDE_SKILL_DIR}/scripts/triagekit.py" check <run folder>
```

Run it from the workspace root, one plain call (no `&&`, no variables in front). `scan` prints what
the files show, and saves it as `signals.json` in the run folder:

| Field | What |
|---|---|
| `failed`, `unexpected`, `steps` | from result.json: the checks that failed, with the runner's evidence, and each step's host time |
| `owner` | the app's processes and Java packages (from the project, else the package), and the pids the app had in this log |
| `signatures` | crash (`FATAL EXCEPTION`), anr (`ANR in`), native-crash (`Fatal signal`), tombstone (`>>> … <<<`), watchdog, process-died, low-memory-kill and dead-object, each with its time, process, `ours`, `step` (the step it happened during) and `lines` in logcat.log. A crash also has its exception chain, `root` (the last `Caused by`) and `owner_frames` (the frames in the app's packages) |
| `app_errors` | the app's own E and F lines, grouped by tag: lines, reports, exceptions named and frames in the app's code |
| `app_timings` | the app's lines that give a time in ms ("Showing 24 devices after 5088 ms") |
| `crash_files` | each crash-<n>.txt: process, pid, subject |
| `comparable_runs` | other runs of the same, unchanged use case on the same install of the app, with their verdicts |
| `clock` | host time = device time + `host_minus_device_s` (the steps are on the host clock, the log on the device's) |

`scan` finds; it doesn't judge. Read the lines it points to (`Read` logcat.log at those lines),
and look at the failed step's screenshot.

## The classes

Pick **one** class for the failure the use case is about: the first that fits, in this order.

| Class | When |
|---|---|
| `environment` | the run couldn't test the app: verdict `blocked`, the device or Appium failed, a step couldn't be done for a reason outside the app (no network, low-memory kill, a watchdog reset of the system), or a check failed because of the tooling |
| `native-crash` | a `Fatal signal` or a tombstone in the app's process |
| `crash` | `FATAL EXCEPTION` in the app's process, or the app's process died during the run |
| `anr` | `ANR in <the app>`, or an "isn't responding" dialog |
| `flaky` | there are comparable runs and they disagree: some pass, some fail, with no crash, ANR or native crash behind the failures. (An intermittent crash is still a `crash`: give the rate in `repro`) |
| `error-dialog` | the app showed an error dialog (its own or the system's) and didn't crash |
| `slow` | it happened, but later than the use case allows: a measured time over the limit |
| `timeout` | it never happened within the time, and nothing in the log explains it |
| `wrong-screen` | the screen showed the wrong text, value or screen |
| `log-only` | the screen was right, but a check about the log failed (errors from the app) |
| `pass` | every check passed and nothing unexpected happened |

- A failure that fits several classes takes the first one. Note the others in `other_findings`. For
  example, a slow list that also logs icon errors is `slow`, plus a `log-only` finding.
- **Flaky needs runs.** One run can't show it. When the use case has `repeat: N` and fewer runs
  exist, say so (`repro.runs` < `repeat`), and classify what the runs show.
- **A passing run** can still have findings: errors in the log or a dialog that no check covers.
  The class is `pass`, and they go in `other_findings`.

## Whose code (`ours`)

- **true:** the signature is in the app's process **and** the root cause's frames include the app's
  packages (`owner_frames`), or the failure is on the app's screen with the app's own text,
  values or log tags.
- **false:** it is in another process (system_server, another app, a native daemon) and the app's
  code isn't in its frames. Say whose it is (`owner`: the process or package).
- **"unknown":** in the app's process, but every frame is the platform's or a library's. Note the
  last app frame before it, if there is one.

The `owner` is the package or process. For an app project, the module is the app (`:app`).

## The time window

The failure belongs to the step it happened in (`signatures[].step`, or the failed check's step).
Look at the log from the previous step's start to a few seconds after the failure. Anything well
before the run's first step belongs to an earlier run. The log was cleared at the start, so
that is rare.

## What to write

Both files go into the run folder.

**triage.json** (for the next agent and for scoring):

```json
{
  "run": "runs/20261104-094506-01-pairing-bt-off",
  "usecase": "usecases/testbench/01-pairing-bt-off.txt",
  "verdict": "fail",
  "class": "crash",
  "ours": true,
  "owner": "dev.liveview.testbench",
  "summary": "The app crashes when the pairing screen opens with Bluetooth off: NullPointerException in PairingActivity.onResume.",
  "failed_step": {"n": 3, "line": "launch the pairing screen"},
  "signature": "java.lang.NullPointerException at dev.liveview.testbench.PairingActivity.onResume(PairingActivity.kt:30)",
  "frames": ["dev.liveview.testbench.PairingActivity.onResume(PairingActivity.kt:30)"],
  "repro": {"failed": 1, "runs": 1, "compared": []},
  "evidence": [
    {"file": "logcat.log", "lines": "1636-1668", "what": "FATAL EXCEPTION in dev.liveview.testbench"},
    {"file": "crash-1.txt", "what": "the crash report"},
    {"file": "03-tap-pair-a-device.png", "what": "the launcher after the crash"}
  ],
  "other_findings": [],
  "confidence": "high"
}
```

- `signature`: one line that identifies this failure, the same each time it happens: the root
  exception and the first app frame, the ANR's reason, or the check and what was seen.
- `frames`: the app frames from the root cause, top first (for code-fix).
- `repro`: `failed` of `runs`, counting this run and the comparable ones. `compared`: their
  folders.
- `evidence[].file` is a file in the run folder (or a path from the workspace root).
- `other_findings`: `{"class", "summary", "evidence"}` for anything else that is wrong.
- `confidence`: `high` (a signature or a clear screen), `medium`, or `low` (say why in the summary).

**triage.md** (for people, a screen at most):

```markdown
# Triage: <use case title>: <class>

**<summary>**

| | |
|---|---|
| Run | runs/… (verdict, mode) |
| Failed step | 3. launch the pairing screen |
| Class | crash (ours: dev.liveview.testbench) |
| Reproduced | 1 of 1 runs |

## Evidence

<the signature's log lines (10–25 of them), fenced, with line numbers from logcat.log>

- screenshot, crash file: what each shows

## Other findings

## Whose code

<one or two sentences: the frames or the process, and why that makes it ours or not>
```

Then run `triagekit check <run>`: it checks triage.json's fields and that the evidence files
exist. Fix what it lists.
