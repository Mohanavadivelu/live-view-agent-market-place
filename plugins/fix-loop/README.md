# fix-loop

The whole loop: run the use case, triage, fix (Gate 1), build, push (Gate 2), verify, report.

Part of the [live-view-agents](../../README.md) marketplace. **Status: S4**, the report part (see
[PLAN.md](../../PLAN.md)): `/report-usecase` runs a use case, triages it and writes a bug report.
Fixing, pushing and verifying come in S5–S7. Installing it also installs usecase-runner,
log-triage and live-view-mcp.

```
/report-usecase usecases/testbench/07-device-battery.txt
/report-usecase runs/20261104-094506-01-pairing-bt-off
```

| Kind | Name | File | Stage |
|---|---|---|---|
| command | `/report-usecase` | `commands/report-usecase.md`: run (N times for `repeat: N`), triage, report | S4 |
| agent | `reporter` | `agents/reporter.md`: writes `bug-report.md` | S4 |
| skill | `bug-report` | `skills/bug-report/SKILL.md`: the report's format | S4 |
| agent | `orchestrator` | `agents/orchestrator.md` | S7 |
| agent | `verifier` | `agents/verifier.md` | S7 |
| skill | `verify-fix` | `skills/verify-fix/SKILL.md` | S7 |
| command | `/fix-usecase` | `commands/fix-usecase.md` | S7 |

`bug-report.md` goes into the run folder, next to `triage.md`. It says what the user sees, the
steps to reproduce, expected and actual, how often it failed, whose code it is and the evidence,
with links to the screenshots, the log and the screen recording.

## Needs

What usecase-runner and log-triage need. To run `/report-usecase` without permission prompts in
Claude Code:

```json
"permissions": {
  "allow": [
    "mcp__plugin_live-view-mcp_appium",
    "Bash(python *runkit.py*)",
    "PowerShell(python *runkit.py*)",
    "Bash(python *triagekit.py*)",
    "PowerShell(python *triagekit.py*)"
  ]
}
```

## Install

```
/plugin install fix-loop --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install fix-loop@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
