# log-triage

Reads a use case run's files (logcat, crash reports, screenshots, result.json) and says what
failed, what kind of failure it is, whose code it is, and the evidence. It writes `triage.md`
(for people) and `triage.json` (for code-fix, and for scoring) into the run folder.

Part of the [live-view-agents](../../README.md) marketplace. **Status: S4** (see
[PLAN.md](../../PLAN.md)). It reads files only: no device, no code changes.

```
/triage-run runs/20261104-094506-01-pairing-bt-off
```

| Kind | Name | File |
|---|---|---|
| agent | `log-triage` | `agents/log-triage.md` |
| skill | `logcat-triage` | `skills/logcat-triage/SKILL.md`: signatures, classes, whose code, triage.md and triage.json |
| script | `triagekit.py` | `skills/logcat-triage/scripts/triagekit.py`: `scan` (signatures, the app's errors and timings, comparable runs → signals.json), `check` (triage.json) |
| command | `/triage-run` | `commands/triage-run.md` |

## Classes

`crash`, `native-crash`, `anr`, `flaky`, `error-dialog`, `slow`, `timeout`, `wrong-screen`,
`log-only`, `environment` and `pass`. Each triage also says whether the code is the app's
(`ours`: true, false or "unknown"), how often it failed in the comparable runs (the same use case on
the same install of the app), and any other findings.

## Needs

- A run folder from [usecase-runner](../usecase-runner/README.md).
- Python 3.9+ for `triagekit.py`.

To run without permission prompts in Claude Code:

```json
"permissions": {
  "allow": [
    "Bash(python *triagekit.py*)",
    "PowerShell(python *triagekit.py*)"
  ]
}
```

## Install

```
/plugin install log-triage --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install log-triage@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
