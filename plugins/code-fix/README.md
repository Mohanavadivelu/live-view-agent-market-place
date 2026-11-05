# code-fix

Finds the root cause of a triaged failure in the source (file:line), proposes the smallest fix
with a unit test where one can run, and asks you before changing anything (**Gate 1**). After your
Apply, it applies exactly the change you saw, builds the project and runs its unit tests, and
undoes the change if they fail.

Part of the [live-view-agents](../../README.md) marketplace. **Status: S5** (see
[PLAN.md](../../PLAN.md)). Installing it also installs log-triage. Nothing is pushed to a device:
that is build-push (S6, Gate 2).

```
/fix-run runs/20261104-095033-04-settings
```

| Kind | Name | File |
|---|---|---|
| command | `/fix-run` | `commands/fix-run.md`: investigate, Gate 1, apply, build, test |
| agent | `code-investigator` | `agents/code-investigator.md`: root cause and proposal; changes no source |
| agent | `fixer` | `agents/fixer.md`: applies the approved change, builds, tests, undoes on failure |
| skill | `stack-to-source` | `skills/stack-to-source/SKILL.md`: frames, tags, text and timings → the code; native and AOSP |
| skill | `fix-proposal` | `skills/fix-proposal/SKILL.md`: investigation.json, fix.json, Gate 1, fix-result.json |
| script | `sourcekit.py` | `skills/stack-to-source/scripts/sourcekit.py`: `resolve` (frames and tags → file:line and the code) |
| script | `fixkit.py` | `skills/fix-proposal/scripts/fixkit.py`: `propose`, `apply`, `undo`, `build`, `diff` |

## Gate 1

The investigator writes `investigation.md` (the cause, the root cause file:line, the log lines, the
code, the diff, what will be built) and `fix.json`, the change as exact replacements. `fixkit
propose` renders `fix.diff` from it, and that diff is what you approve. `/fix-run` shows it and asks:

- **Apply**: the fixer applies it (only if it still makes exactly that diff), builds and runs the
  unit tests. The originals are kept in the run's `backup-src/`.
- **Change**: say what to change. The investigator revises it, and you are asked again.
- **Stop**: nothing changes.

A failed build or test undoes the change and goes back to the investigator, and to you again. The
change is never committed: that is yours to do.

## The run folder, after a fix

`investigation.json`, `investigation.md`, `fix.json`, `fix.diff`, `backup-src/`, `build.log`,
`test.log`, `build-result.json`, `applied.diff` and `fix-result.json`, next to the run's and
triage's files.

## Needs

- A triaged run folder (log-triage) and a project config (`projects/<name>.json`, see
  `projects/schema.json`) with `source_roots`, `tests` and `build`.
- Python 3.9+, and what the project's build needs (for the test bench: the JDK through `JAVA_HOME`).

To run without permission prompts in Claude Code (Gate 1 still asks):

```json
"permissions": {
  "allow": [
    "Bash(python *sourcekit.py*)",
    "PowerShell(python *sourcekit.py*)",
    "Bash(python *fixkit.py*)",
    "PowerShell(python *fixkit.py*)"
  ]
}
```

## Install

```
/plugin install code-fix --marketplace Mohanavadivelu/live-view-agent-market-place
```

Or after `/plugin marketplace add Mohanavadivelu/live-view-agent-market-place`: `/plugin install code-fix@live-view-agents`.
VS Code: see [docs/install-vscode.md](../../docs/install-vscode.md).
