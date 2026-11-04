# Changelog

All notable changes to the live-view-agents marketplace are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The plan: [PLAN.md](PLAN.md) (stages S0–S9).
- S0, skeleton: the marketplace catalog (`.claude-plugin/marketplace.json`, name `live-view-agents`) with six
  plugins (live-view-mcp, usecase-runner, log-triage, code-fix, build-push, fix-loop), each with its
  manifest and a README of what it will hold; `scripts/validate.py` and the CI that runs it; install
  docs for Claude Code and VS Code.
- S1, live-view-mcp 0.0.2: `.mcp.json` connects appium-mcp (`appium`, `http://127.0.0.1:8000/mcp`);
  the **env-doctor** agent checks appium-mcp, the device, the screen, an Appium session (started
  and ended) and whether system push is possible, and says what to fix; **/check-setup** runs it;
  the **device-safety** skill holds the device rules (which device, never, ask first, backup before
  a push, one run per device, leave it as found). `docs/writing-agents.md`: the files, how
  appium-mcp's tools are named and why agents use their short names, trying a plugin with
  `--plugin-dir`.
- S2, the test bench: **LV Test Bench** (`testbench/`, Kotlin, framework Views, minSdk 30, no
  libraries): Home, Pairing, My devices, a device's details, Settings, with seven planted bugs
  (a crash with Bluetooth off, an ANR on Scan, a wrong string, an error dialog, errors only in the
  log, a slow list, a race that fails about half the time) and three unit tests. One plain-text use
  case per bug in `usecases/testbench/`; `projects/lv-testbench.json` (build with Gradle, data push:
  `adb push` + `pm install`); the answer key `eval/answers/testbench.json`, written by
  `eval/make_answers.py` from the code; `testbench/reset-bugs.ps1`. Each use case was done by hand
  through appium-mcp on the Android 17 emulator and showed its bug.

