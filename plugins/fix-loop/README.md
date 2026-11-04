# fix-loop

The whole loop: run the use case, triage, fix (Gate 1), build, push (Gate 2), verify, report.

Part of the [live-view-agents](../../README.md) marketplace. **Status: planned for stage S7** (see [PLAN.md](../../PLAN.md));
installs today, with nothing in it yet.

| Kind | Name | File |
|---|---|---|
| agent | `orchestrator` | `agents/orchestrator.md` |
| agent | `verifier` | `agents/verifier.md` |
| agent | `reporter` | `agents/reporter.md` |
| skill | `verify-fix` | `skills/verify-fix/SKILL.md` |
| skill | `bug-report` | `skills/bug-report/SKILL.md` |
| command | `/fix-usecase` | `commands/fix-usecase.md` |

## Install

```
/plugin install fix-loop --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install fix-loop@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
