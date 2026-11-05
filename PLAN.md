# Plan: live-view agent marketplace

Agents and skills that test Android use cases through **appium-mcp** (from
[adb-remote](https://github.com/Mohanavadivelu/adb-remote): live-view-app → Tools → appium-mcp),
find the issue in the logs and the code, fix it, build, **adb push** it to the device and verify it.
Installable as plugins in **Claude Code**, **VS Code** (Copilot chat) and **Copilot CLI / the Copilot app**.

Status: S0–S6 done; S7 (fix-loop) next. Each stage below ends tested in Claude Code and VS Code, and is committed on its own.

## Decisions so far

| Question | Decision |
|---|---|
| What gets deployed | **adb push**: the built files to their device paths, then a restart (no full flash) |
| Which projects | **Any project**: a project config file says how to build and where to push |
| Use cases | **Plain text**, a line per step: `disable BT` / `launch pairing screen` / `expect: …` |
| Autonomy | Ask **before changing code** (Gate 1) and again **before pushing** (Gate 2) |
| Format | Written once in the **Claude plugin format** (Claude Code and VS Code read it); the **Copilot format** is generated |

## The loop

```
use case ─► Runner ─► Triage ─┬─ pass ───────────────────────────────────────► Reporter
                               └─ our code ─► Investigator ─► GATE 1 ─► Fixer ─► Builder
                                                                                    │
              Verifier ◄─ Pusher (adb push, restart) ◄─ GATE 2 ◄────────────────────┘
                 │
                 └─ still failing: back to Triage (3 rounds at most) ─► Reporter
```

- **Gate 1** (before changing code): the triage summary and log excerpt, the root cause (file:line),
  the proposed diff and the module. Apply · Change (with a note) · Stop and report.
- **Gate 2** (before pushing): the build result, each file → device path, the backup taken, the
  restart method, the device. Push · Push and reboot · Stop.
- **Run folder** per use case: `runs/<date>-<case>/` with logcat.log, screen.mp4, step screenshots,
  steps.json (the actions as replayed), triage.md, fix.diff, backup/, bug-report.md.

## What each tool reads

| Tool | Reads | Install |
|---|---|---|
| Claude Code | `.claude-plugin/marketplace.json`; per plugin `.claude-plugin/plugin.json`, `agents/`, `skills/`, `commands/`, `.mcp.json` | `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place` |
| VS Code (Copilot chat) | the same Claude format | `"chat.plugins.marketplaces": ["Mohanavadivelu/live-view-agent-market-place"]` |
| Copilot CLI / Copilot app | Copilot format: `plugin.json`, `skills/`, `mcp.json`, `com.github.copilot/agents/*.agent.md` | generated into `copilot/` |

Skills (`SKILL.md`) are the same format everywhere. Agents differ in their frontmatter and in how
they name MCP tools: `scripts/build-copilot.py` converts them.

## Folder structure

```
.claude-plugin/marketplace.json   the catalog (Claude Code + VS Code)
plugins/
  live-view-mcp/      appium-mcp connection (.mcp.json), env-doctor, device-safety, /check-setup
  usecase-runner/     usecase-runner, usecase-format, run-procedure, /run-usecase
  log-triage/         log-triage, logcat-triage
  code-fix/           code-investigator (read-only), fixer, stack-to-source, fix-proposal, /fix-run
  build-push/         builder, pusher, project-config, build-module, adb-push-deploy, /push-run, /rollback-run
  fix-loop/           orchestrator, verifier, reporter, verify-fix, bug-report, /fix-usecase
copilot/              GENERATED: the Copilot format of the same plugins
projects/             project configs: schema.json, example-aosp.json, lv-testbench.json, lv-testbench-system.json
usecases/             examples/ and testbench/ (plain text)
testbench/            the Android test app with planted bugs
eval/                 answer key (outside every source root), score.py, results/
scripts/              build-copilot.py, validate.py, new-plugin.py
docs/                 install for each tool, writing agents, the fix loop
.github/workflows/    validate.yml
runs/                 run folders (git-ignored)
```

## Stages

### S0. Skeleton

The repo installs as a marketplace in each tool, with empty plugins.

- [x] `.claude-plugin/marketplace.json` listing the six plugins
- [x] each plugin: `.claude-plugin/plugin.json` (name, version, description), empty `agents/` `skills/`
- [x] `scripts/validate.py`: manifests parse, versions match, skill names = folder names, frontmatter present
- [x] `.github/workflows/validate.yml`
- [x] `README.md` (what's in it, the plugins table, install for each tool), `CHANGELOG.md`, `.gitignore` (`runs/`, `eval/results/`)
- [x] `docs/install-claude-code.md`, `docs/install-vscode.md`

Done when: Claude Code (`/plugin marketplace add` + `/plugin install`) and VS Code (`chat.plugins.marketplaces`) both list and install the six plugins.

### S1. live-view-mcp: connect and check

- [x] `plugins/live-view-mcp/.mcp.json`: `appium` → `http://127.0.0.1:8000/mcp`
- [x] find out the names plugin MCP tools get in Claude Code and VS Code (namespacing); write it down in `docs/writing-agents.md`
- [x] `agents/env-doctor.md`: appium-mcp reachable, device online (`select_device`), Appium driver, screen awake, adb root possible
- [x] `skills/device-safety/SKILL.md`: allowed serials, no factory reset / wipe, back up before push, one run per device
- [x] `commands/check-setup.md`: `/check-setup` runs env-doctor and says what to fix

Done when: `/check-setup` reports the emulator and appium-mcp correctly in Claude Code and VS Code, and says clearly when appium-mcp isn't running.

### S2. Test bench (the target to prove the loop on)

- [x] `testbench/`: LV Test Bench (Kotlin, Views, minSdk 30): Home, Pairing, Devices, Device details, Settings
- [x] the 7 planted bugs: crash on Pairing with BT off, ANR on Scan, wrong string, error dialog, log-only, slow list, flaky race
- [x] `usecases/testbench/*.txt`: one plain-text use case per bug
- [x] `projects/lv-testbench.json`: build `gradlew :app:assembleDebug`, push mode `data` (push + `pm install`)
- [x] `eval/answers/testbench.json`: per bug the class, owner, file:line, the fix
- [x] `testbench/reset-bugs.ps1`

Done when: it builds, installs with the data push, and each use case shows its bug when done by hand through appium-mcp.

Found while building it (for the later stages):

- **S3:** Appium waits for the app to be idle before each action, so a second tap during a frozen
  main thread arrives late. The ANR still happens (input dispatching timed out), but on this
  emulator **no "isn't responding" dialog shows**: ANRs are found in the log (`ANR in`) and
  `adb_crashes`, not on screen.
- **S3:** "disable BT" = `cmd bluetooth_manager disable` (needs `ADB_SHELL_MODE=full`, or adb from the
  terminal); `adb_shell` in safe mode refuses some quoting (`grep -E "a|b"`).
- **S3/S4:** My devices logs `I/Devices: Loading the devices` and `Showing 24 devices after N ms`:
  timing comes from the log, not from polling the screen.
- **S6:** Git Bash rewrites device paths (`/data/local/tmp/…` → `C:/Program Files/Git/data/…`):
  run adb with `MSYS_NO_PATHCONV=1`, or from PowerShell.
- The build needs the network once (Gradle downloads aapt2 for AGP 9.4.1); JDK: Android Studio's
  `jbr` (JDK 25) through `JAVA_HOME`.

### S3. usecase-runner: run a plain-text use case

- [x] `skills/usecase-format/SKILL.md`: the plain-text rules, `expect:`, common phrases ("disable BT", "launch X screen") and how they're done, the `steps.json` replay format
- [x] `skills/run-procedure/SKILL.md`: preconditions, logcat recording + screen recording, screenshot per step, error-dialog check, the run folder
- [x] `agents/usecase-runner.md`: interprets lines (first run) or replays `steps.json` (reruns); falls back to interpreting when the screen changed
- [x] `commands/run-usecase.md`: `/run-usecase <file>`

Done when: the 7 test bench use cases run unattended, each leaving a complete run folder, and a rerun replays `steps.json`.
- [x] `skills/run-procedure/scripts/runkit.py`: run folder, lock, device state, adb beyond safe mode, timed sequences, collecting appium-mcp's files

Found while building it:

- A command is a skill too: a command and a skill with the same name clash (validate.py checks it).
- Unattended runs can't chain shell commands or copy out of appium-mcp's work folder (outside the
  workspace), so the mechanics are one script (`runkit.py`) and one permission
  (`Bash(python *runkit.py*)`).
- Tool calls take seconds: `tap / wait 2 s / tap` done call by call puts 8 s between the taps.
  Taps, keys and waits in a row run as one `runkit seq` (one adb shell, timed on the device).
- Taps go through `input tap`: Appium's own taps wait for the app to be idle, which hides ANRs.
- Launches are cold starts (force stop, then start): a resumed task shows where an earlier run
  left the app.
- A run costs about $0.7–1.1 and 1–2.5 minutes. All 7 use cases fail on their bug, unattended,
  with complete run folders, and a rerun of 02 replays steps.json.

### S4. log-triage + a first report

- [x] `skills/logcat-triage/SKILL.md`: signatures (FATAL EXCEPTION, ANR in, tombstone/SIGSEGV, watchdog, "has died", Binder/DeadObject), owner by package/pid/tag, the time window around the failed step
- [x] `agents/log-triage.md`: class (crash / ANR / native crash / error dialog / wrong screen / timeout / flaky / environment), owning module, "our code?", the evidence → `triage.md`
- [x] `plugins/fix-loop/agents/reporter.md` + `skills/bug-report/SKILL.md` (report only, no fix yet)
- [x] `eval/score.py` (classification part)

Done when: triage classifies all 7 test bench bugs correctly and writes a readable report for each ("run it and tell me what broke" works).
- [x] `skills/logcat-triage/scripts/triagekit.py`: `scan` (signatures, the app's pids, errors and timings, comparable runs → signals.json), `check` (triage.json)
- [x] `commands/triage-run.md` (log-triage) and `commands/report-usecase.md` (fix-loop): run (N times for `repeat: N`), triage, report

Found while building it:

- A subagent can't write `report.md` or `summary.md` (Claude Code refuses it), so the report is
  `bug-report.md`.
- Flaky needs several runs on the same build: use cases say `repeat: N`, and device.json records
  the app's install time so that runs on another build aren't compared.
- Triage reached for `python -c` and chained shell commands to reason about the log; those need
  approvals, so it is told to use Read and Grep only.
- The runner can't tell the time (`date` needs approval) and guessed `since_seconds 60`:
  `runkit since <run>` gives it.
- Result: `eval/score.py` gives class 7/7, ours 7/7, reports 7/7. 07 ran 5 times with
  `/report-usecase`: 4 fails, 1 pass, so it was classed flaky. The others were triaged from their
  S3 runs, plus a fresh end-to-end run of 03. Triage costs about $0.8, a triage and report together
  about $1.1–1.6, and 07's five runs with triage and report $6.2.

### S5. code-fix: root cause and Gate 1

- [x] `projects/schema.json`: source roots, build, push, restart, device (shared with S6)
- [x] `skills/stack-to-source/SKILL.md`: Java/Kotlin frames → file:line, tag → class by grep, R8 retrace, native via `addr2line`/`ndk-stack`, AOSP module via `module-info.json`
- [x] `agents/code-investigator.md` (read-only): root cause + proposed diff → asks **Gate 1**
- [x] `agents/fixer.md`: applies the approved diff, adds a unit test where the module has tests
- [x] score: right file:line, the fix compiles

Done when: for the test bench bugs the investigator points at the right file:line and, after Gate 1, the fixer's change builds.
- [x] `skills/fix-proposal/SKILL.md` + `scripts/fixkit.py` (propose, apply, undo, build, diff), `skills/stack-to-source/scripts/sourcekit.py` (resolve), `commands/fix-run.md`: investigate, Gate 1, apply, build, test

Found while building it:

- A subagent can't ask the user, so the command asks Gate 1. A run with nobody to answer stops at
  the gate, and the fixer stops when it isn't told that the user approved.
- The change is `fix.json` (exact replacements), and `fix.diff` is rendered from it, so a diff can't
  be hand-written wrong. `apply` refuses a fix.json that no longer makes the diff that was shown.
- My first skill text used the test bench's own bugs as examples, and the first proposal for B4
  simply copied its example. The examples in every skill are now from a made-up notes app. The test
  bench score is still a best case, because the same person planted the bugs and wrote the skills:
  **the first real project is the real test.**
- Windows may not look in the current folder for a command (`NoDefaultCurrentDirectoryInExePath`), so
  fixkit runs the project's `gradlew.bat` by its full path.
- Result: `eval/score.py` gives root cause 7/7 and builds 7/7. The new unit tests (B4, B6) fail
  without their fix. **A green build doesn't show the bug is gone:** that is the verifier's job (S7).
  For the eval, the Apply was given in the prompt, and each change was undone afterwards. The live
  question (AskUserQuestion, Change, a failed build going back through the gate) still needs a
  person to try it. An investigation costs about $0.6–1.2, and a fixer about $0.4.

### S6. build-push: build, Gate 2, adb push

- [x] `skills/project-config/SKILL.md`, `projects/example-aosp.json`
- [x] `skills/build-module/SKILL.md` + `agents/builder.md`: build the affected module(s), list artifact → device path + checksum
- [x] `skills/adb-push-deploy/SKILL.md` + `agents/pusher.md`: asks **Gate 2**; `adb root`, `remount` (first time `disable-verity` + reboot), back up with `adb pull`, push, chmod/chown, checksum on the device, restart (force-stop / `stop; start` / reboot), wait for the device, roll back from the backup
- [x] data mode on the current emulator; system mode on a **Google APIs** emulator started with `-writable-system` (the current one is a user build: no adb root)

Done when: a fixed test bench build is pushed in both modes, the device comes back, and a rollback restores the original files.
- [x] `scripts/buildkit.py` (build), `scripts/pushkit.py` (plan, push, status, rollback), `commands/push-run.md` and `commands/rollback-run.md`: the command asks the gate

Found while building it:

- **The device is "up" later than it looks.** After `stop; start`, `sys.boot_completed` stays 1, the
  package manager answers at about 6 s, `mBooted=true` comes at about 12 s, `/sdcard` at about 20 s,
  and only then does an ordinary app exist (the user is unlocked; before that the screen is
  `FallbackHome`). My first check returned at 6 s and called the device ready, with "Too early to
  start activity" still to come. Only using the app right after the push showed it.
- A device with a PIN never unlocks by itself, so that wait ends after 60 s without a rollback. **This
  has not been tried on a device with a PIN.**
- A build tool leaves a file alone when the source's content is what it last built from, so "older
  than the source" (a fix undone and applied again) is a warning at Gate 2, not an error.
- The plan is what is approved, like fix.diff: `push` refuses if the files, the config or the device
  aren't the ones in it, or if the latest build failed.
- A second push from a run keeps the first backup, so a rollback goes back to the original.
- The worst case was tried on the throwaway emulator: a broken `services.jar` stops the framework
  from coming back, and pushkit puts the original back by itself (same sha256, app working).
- The rollback after that test took about 10 minutes, against about 25 s for a clean one. The likely
  cause is the framework recompiling after services.jar's change, but that isn't confirmed.
- The API 37 Google APIs image is 2.0 GB, so the second emulator is API 34 (1.5 GB): `LV_System`.
- Result: data mode pushed the B3 fix to emulator-5554 and use case 03 passed on it. The rollback put
  the original APK back byte for byte, and the app's data survived both. System mode on `LV_System`:
  a new system app, then a replaced one with the fix showing on screen, then back to the unfixed
  title, then removed, with mode, owner and SELinux context as they should be. For these tests the
  yes at the gates was given in the prompt, on the test bench only. The live question and a real
  device still need a person to try them. A builder or pusher costs about $0.3–0.5.

### S7. fix-loop: close the loop

- [ ] `skills/verify-fix/SKILL.md` + `agents/verifier.md`: replay ×3, compare crash signatures before/after, run the module's neighbouring use cases
- [ ] `agents/orchestrator.md`: run → triage → (Gate 1) fix → build → (Gate 2) push → verify, 3 rounds at most, the run folder
- [ ] `commands/fix-usecase.md`: `/fix-usecase <file>`
- [ ] `eval/score.py`: every stage, end to end

Done when: `/fix-usecase` takes each of the 7 test bench bugs from failing to verified with only the two approvals, and the score is recorded.

### S8. Copilot format

- [ ] `scripts/build-copilot.py`: Claude format → `copilot/` (plugin.json, skills, mcp.json, `com.github.copilot/agents/*.agent.md`, MCP tool names)
- [ ] CI: `copilot/` is up to date
- [ ] `docs/install-copilot-cli.md`

Done when: Copilot CLI installs the plugins from `copilot/` and `/run-usecase` (S3) works there.

### S9. Release 0.1.0

- [ ] README complete (plugins, install for each tool, the fix loop, safety)
- [ ] scores of the last eval run in `docs/`
- [ ] tag `v0.1.0`

## To do

The stages still open are S7, S8 and S9 above. Besides those, from the stages already done:

- [ ] Answer Gate 1 live in `/fix-run`: Apply, Change, and a failed build going back through the gate (S5)
- [ ] Answer Gate 2 live in `/push-run`, and the question in `/rollback-run` (S6)
- [ ] Push to a real device, not an emulator (S6)
- [ ] Push to a device with a PIN: after 60 s locked, pushkit treats it as up and doesn't roll back (S6)
- [ ] Find out why the rollback after the broken `services.jar` test took about 10 minutes, against about 25 s for a clean one (S6)
- [ ] Try `projects/example-aosp.json` on a real AOSP tree: it has never been built or pushed (S6)
- [ ] Make B6's unit test independent of timing: it checks that the sort takes under 2 s (S5)
- [ ] Check the plugins in VS Code (`/check-setup`, the tool names): each stage should end tested there too, and so far only Claude Code has been tried

## Open questions

- [x] The name of plugin MCP tools: Claude Code `mcp__plugin_live-view-mcp_appium__<tool>` (see docs/writing-agents.md). VS Code's is still to check.
- [ ] The Copilot marketplace manifest path (GitHub's docs don't name it yet) (S8).
- [x] May S6 download the Google APIs x86_64 system image and create a second emulator for system push? Yes: API 34 (1.5 GB), emulator `LV_System`.
- [x] The JDK for the test bench: Android Studio's `jbr` through `JAVA_HOME` (already set).
- [ ] A first real project for `projects/` after the test bench (which product, its source root, build command, push paths)?
