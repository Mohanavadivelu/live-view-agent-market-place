# Install in Claude Code

```
/plugin marketplace add Mohanavadivelu/live-view-agent-market-place
/plugin install fix-loop@live-view-agents
```

Install single plugins the same way (`<plugin>@live-view-agents`): for example only `usecase-runner` and
`log-triage` for "run it and tell me what broke". `/plugin` lists what is installed; `/plugin marketplace
update live-view-agents` gets new versions.

From a local checkout (while developing):

```
/plugin marketplace add D:/new-github-workspace/live-view-agent-market-place
```

Or on the command line: `claude plugin marketplace add <repo or path>`, then
`claude plugin install <plugin>@live-view-agents`.

The agents talk to appium-mcp: start it in live-view-app (Tools → appium-mcp → Start).
