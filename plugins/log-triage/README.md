# log-triage

Reads a run's logcat, crashes and ANRs: what failed, what kind of failure, and whose code it is.

Part of the [live-view-agents](../../README.md) marketplace. **Status: planned for stage S4** (see [PLAN.md](../../PLAN.md));
installs today, with nothing in it yet.

| Kind | Name | File |
|---|---|---|
| agent | `log-triage` | `agents/log-triage.md` |
| skill | `logcat-triage` | `skills/logcat-triage/SKILL.md` |

## Install

```
/plugin install log-triage --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install log-triage@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
