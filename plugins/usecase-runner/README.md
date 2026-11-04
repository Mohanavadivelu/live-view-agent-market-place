# usecase-runner

Runs a plain-text use case ("disable BT / launch pairing screen") on the device, recording logcat and the screen.

Part of the [live-view-agents](../../README.md) marketplace. **Status: planned for stage S3** (see [PLAN.md](../../PLAN.md));
installs today, with nothing in it yet.

| Kind | Name | File |
|---|---|---|
| agent | `usecase-runner` | `agents/usecase-runner.md` |
| skill | `usecase-format` | `skills/usecase-format/SKILL.md` |
| skill | `run-usecase` | `skills/run-usecase/SKILL.md` |
| command | `/run-usecase` | `commands/run-usecase.md` |

## Install

```
/plugin install usecase-runner --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install usecase-runner@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
