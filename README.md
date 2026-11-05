# live-view agent marketplace

Agents and skills that run Android use cases on a device through
[appium-mcp](https://github.com/Mohanavadivelu/adb-remote/tree/main/appium-mcp), find the issue in the
logs and the code, fix it, **adb push** it to the device and verify it. One marketplace for **Claude
Code**, **VS Code** (Copilot chat agent plugins) and, from stage S8, **Copilot CLI / the Copilot app**.

> **Status: S0–S5 done.** A use case runs unattended on the device, `/report-usecase` triages what
> broke and writes a bug report, and `/fix-run` finds the root cause, asks you (Gate 1), applies the
> fix and builds it. Pushing (S6) and the whole loop (S7) are next. The plan and the stages are in
> [PLAN.md](PLAN.md).

## Plugins

| Plugin | What it does | Stage |
|---|---|---|
| [live-view-mcp](plugins/live-view-mcp/README.md) | Connects to appium-mcp (live-view-app → Tools → appium-mcp) and checks the setup: device, Appium, adb root. | S1 |
| [usecase-runner](plugins/usecase-runner/README.md) | Runs a plain-text use case ("disable BT / launch pairing screen") on the device, recording logcat and the screen. | S3 |
| [log-triage](plugins/log-triage/README.md) | Reads a run's logcat, crashes and ANRs: what failed, what kind of failure, and whose code it is. | S4 |
| [code-fix](plugins/code-fix/README.md) | Finds the root cause in the source (file:line), proposes a fix and, after your approval, applies it. | S5 |
| [build-push](plugins/build-push/README.md) | Builds the changed module and, after your approval, adb pushes it to the device, restarts it and can roll back. | S6 |
| [fix-loop](plugins/fix-loop/README.md) | The whole loop: run the use case, triage, fix (Gate 1), build, push (Gate 2), verify, report. `/report-usecase` (run, triage, bug report) works now. | S4, S7 |

A use case is plain text, a line per step:

```
disable BT
launch pairing screen
expect: the pairing screen shows "Pair new device"
```

The fix loop asks you twice: **before changing code** and **before pushing** to the device.

## Install

- Claude Code: [docs/install-claude-code.md](docs/install-claude-code.md)
- VS Code: [docs/install-vscode.md](docs/install-vscode.md)

The agents need appium-mcp running: in [live-view-app](https://github.com/Mohanavadivelu/adb-remote/tree/main/live-view-app),
Tools → appium-mcp → Start (it listens on `http://127.0.0.1:8000/mcp`).

## Develop

```bash
python scripts/validate.py      # the catalog, manifests, agents, skills and commands
python eval/score.py            # scores the newest triaged runs against eval/answers/
```

Layout: `.claude-plugin/marketplace.json` (the catalog), `plugins/<name>/` (each plugin:
`.claude-plugin/plugin.json`, `agents/`, `skills/<name>/SKILL.md`, `commands/`, `.mcp.json`).
