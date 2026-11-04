# code-fix

Finds the root cause in the source (file:line), proposes a fix and, after your approval, applies it.

Part of the [live-view-agents](../../README.md) marketplace. **Status: planned for stage S5** (see [PLAN.md](../../PLAN.md));
installs today, with nothing in it yet.

| Kind | Name | File |
|---|---|---|
| agent | `code-investigator` | `agents/code-investigator.md` |
| agent | `fixer` | `agents/fixer.md` |
| skill | `stack-to-source` | `skills/stack-to-source/SKILL.md` |

## Install

```
/plugin install code-fix --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install code-fix@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
