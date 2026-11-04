# live-view-mcp

Connects appium-mcp (live-view-app → Tools → appium-mcp) and checks the setup with /check-setup: the device, Appium, and whether system push is possible. The device-safety rules every plugin follows.

Part of the [live-view-agents](../../README.md) marketplace. **Status: S1 done** (see [PLAN.md](../../PLAN.md)).

Needs appium-mcp running: in live-view-app, **Tools → appium-mcp → Start** (`http://127.0.0.1:8000/mcp`).
Then `/check-setup` (or `/live-view-mcp:check-setup`), optionally with a device serial.

| Kind | Name | File |
|---|---|---|
| agent | `env-doctor` | `agents/env-doctor.md` |
| skill | `device-safety` | `skills/device-safety/SKILL.md` |
| MCP server | `appium` | `.mcp.json` |
| command | `/check-setup` | `commands/check-setup.md` |

## Install

```
/plugin install live-view-mcp --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install live-view-mcp@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
