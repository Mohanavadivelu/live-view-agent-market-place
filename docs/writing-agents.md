# Writing agents, skills and commands

The plugins are written once in the Claude plugin format. Claude Code and VS Code read it as it is.
The Copilot format is generated from it (stage S8).

## Files

| Kind | File | Frontmatter |
|---|---|---|
| agent | `plugins/<plugin>/agents/<name>.md` | `name` (= the file name), `description` |
| skill | `plugins/<plugin>/skills/<name>/SKILL.md` | `name` (= the folder name), `description` |
| command | `plugins/<plugin>/commands/<name>.md` | `description`, optional `argument-hint` |
| MCP server | `plugins/<plugin>/.mcp.json` | `mcpServers` |

The `description` is what the tool matches requests against. It says what the thing does **and
when to use it**. `python scripts/validate.py` checks all of this. CI runs it.

- **A command is a skill too.** `/run-usecase` and a skill called `run-usecase` in the same plugin
  clash, so the skill is `run-procedure`.
- **Agents preload skills** with `skills:` in their frontmatter, by plugin-qualified name
  (`usecase-runner:run-procedure`, `live-view-mcp:device-safety`). VS Code may ignore it, so the
  agent's text also says which skills to load.
- **Dependencies:** `"dependencies": ["live-view-mcp"]` in plugin.json installs and enables
  live-view-mcp with the plugin (`+ 1 dependency`).
- **Scripts** live in a skill's folder and are called as `python "${CLAUDE_SKILL_DIR}/scripts/<x>.py"`.
- **A chain of agents is a command.** A subagent can't start another one, so `/report-usecase`
  (runner, then log-triage, then reporter) is a command that uses each agent in turn.
- **A subagent can't write `report.md`, `REPORT.md` or `summary.md`.** Claude Code refuses the Write
  ("Subagents should return findings as text"). Other names work, so the report is `bug-report.md`.

## appium-mcp's tools: name them by their short name

appium-mcp is connected once, by live-view-mcp's `.mcp.json` (server `appium`,
`http://127.0.0.1:8000/mcp`). The full name of a tool depends on where the server comes from:

| Connected by | Tool name | Verified |
|---|---|---|
| the live-view-mcp plugin in Claude Code | `mcp__plugin_live-view-mcp_appium__select_device` | ✔ (Claude Code 2.1.317) |
| a project's or user's own `.mcp.json` (`appium`) | `mcp__appium__select_device` | ✔ |
| VS Code | `<server>/<tool>`, shown in the chat's tool picker | not yet |

So agents:

- name tools by their short name in the text (`select_device`, `adb_shell`) and say that the
  prefix varies (see env-doctor);
- don't list appium-mcp tools in a `tools:` frontmatter field, because a list made for one naming
  hides the tools under another.

In Claude Code, the server shows in `/mcp` as `plugin:live-view-mcp:appium`. Agents are
`live-view-mcp:env-doctor`, and commands are `/live-view-mcp:check-setup` (or `/check-setup` when
no other plugin has one).

A project that already connects appium-mcp itself (adb-remote's `.mcp.json`) gets the tools twice,
under both names. That is harmless: both reach the same server.

## Unattended agents and permissions

An agent that runs unattended (usecase-runner) does all its shell work through one script
(`runkit.py`), one plain call at a time, for these reasons:

- **Prefix rules can't cover chains.** `a && b`, `X=1 adb …`, and `cp` or `Copy-Item` out of
  appium-mcp's work folder (outside the workspace) each need their own approval.
- **One rule then covers everything:** `Bash(python *runkit.py*)` (and the same for PowerShell),
  next to `mcp__plugin_live-view-mcp_appium`.
- **The script checks its own input.** For example, `seq` accepts only taps, swipes, keys and
  waits.

## The two gates

An agent that changes code asks first (Gate 1), and an agent that pushes to a device asks again
(Gate 2). See [PLAN.md](../PLAN.md#the-loop). A gate shows what will happen and waits for a yes. It
never assumes one from an earlier answer. The device rules are in the `device-safety` skill.

## Trying a plugin without installing it

```bash
claude -p "/live-view-mcp:check-setup" --plugin-dir plugins/live-view-mcp \
  --allowedTools "mcp__plugin_live-view-mcp_appium"
```

Run it from a folder with no `.mcp.json` of its own, so that only the plugin's tools are there.
`--output-format stream-json --verbose` shows each tool call.
