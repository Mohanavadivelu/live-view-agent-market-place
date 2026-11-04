# Install in VS Code (Copilot chat)

VS Code reads this marketplace as it is (it supports the Claude plugin format). Agent plugins are a
preview feature: turn them on, then add the marketplace in your settings (`Ctrl+,` → the `{}` icon
for settings.json):

```json
"chat.plugins.enabled": true,
"chat.plugins.marketplaces": ["Mohanavadivelu/live-view-agent-market-place"]
```

Then in the Chat view: **Customize** → plugins → install the ones you want. Plugin IDs are
`<plugin>@live-view-agents`.

From a local checkout (while developing), point at the folder instead:

```json
"chat.plugins.marketplaces": ["file:///D:/new-github-workspace/live-view-agent-market-place"]
```

The agents talk to appium-mcp: start it in live-view-app (Tools → appium-mcp → Start).
