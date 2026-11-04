# live-view-mcp

Connects to appium-mcp (live-view-app → Tools → appium-mcp) and checks the setup: device, Appium, adb root.

Part of the [live-view-agents](../../README.md) marketplace. **Status: planned for stage S1** (see [PLAN.md](../../PLAN.md));
installs today, with nothing in it yet.

| Kind | Name | File |
|---|---|---|
| agent | `env-doctor` | `agents/env-doctor.md` |
| skill | `device-safety` | `skills/device-safety/SKILL.md` |
| command | `/check-setup` | `commands/check-setup.md` |

## Install

```
/plugin install live-view-mcp --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install live-view-mcp@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
