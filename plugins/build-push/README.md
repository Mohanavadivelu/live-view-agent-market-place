# build-push

Builds the changed module and, after your approval, adb pushes it to the device, restarts it and can roll back.

Part of the [live-view-agents](../../README.md) marketplace. **Status: planned for stage S6** (see [PLAN.md](../../PLAN.md));
installs today, with nothing in it yet.

| Kind | Name | File |
|---|---|---|
| agent | `builder` | `agents/builder.md` |
| agent | `pusher` | `agents/pusher.md` |
| skill | `project-config` | `skills/project-config/SKILL.md` |
| skill | `build-module` | `skills/build-module/SKILL.md` |
| skill | `adb-push-deploy` | `skills/adb-push-deploy/SKILL.md` |

## Install

```
/plugin install build-push --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install build-push@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
