---
name: fix-proposal
description: How a code fix is proposed, approved and applied. It covers investigation.json and investigation.md (the root cause), fix.json (the change as exact replacements) and fix.diff, what Gate 1 shows and its three answers, applying only the approved change with a backup, building and running the unit tests, undoing, and fix-result.json. Uses the fixkit.py helper. Use when proposing a fix for a triaged run, asking for approval, or applying an approved fix.
---

# Proposing and applying a fix

Nothing in the source changes until the user has seen the change and said yes: **Gate 1**. The
change that is applied is exactly the one shown, because both come from the same `fix.json`.

```
python "${CLAUDE_SKILL_DIR}/scripts/fixkit.py" <command> <run folder>
```

Run it from the workspace root, one plain call at a time.

| Command | Does |
|---|---|
| `propose` | checks `fix.json` (each `old` text occurs once, every file is in the source roots or the tests folder) and writes `fix.diff` |
| `apply` | applies `fix.json`, only if it still makes exactly `fix.diff`. The originals go to `backup-src/` |
| `build` | the project's `build.command`, then `build.test` → `build.log`, `test.log`, `build-result.json`, with the compiler's errors |
| `diff` | the change as applied → `applied.diff` |
| `undo` | puts the originals back from `backup-src/` and removes created files |

## The investigation (written by the investigator)

**investigation.json** (the examples are from a notes app, `com.example.notes`):

```json
{
  "run": "runs/20261102-101500-03-note-words",
  "class": "wrong-screen",
  "root_cause": {"file": "app/src/main/java/com/example/notes/data/NoteStats.kt",
                 "line": 12, "function": "NoteStats.wordCount",
                 "code": "fun wordCount(text: String): Int = text.split(\" \").size"},
  "also": [{"file": "app/src/main/java/com/example/notes/EditorActivity.kt", "line": 57,
            "why": "shows wordCount() as the footer"}],
  "cause": "split(\" \") on an empty note gives one empty piece, so a new note's footer says \"1 word\".",
  "module": ":app",
  "fix": "wordCount() counts only the non-empty pieces between runs of white space.",
  "test": "NoteStatsTest.emptyNoteHasNoWords: \"\" and \"  \" give 0, \"a  b\" gives 2.",
  "confidence": "high",
  "risks": "Words split by tabs or new lines now count too, which is what the footer means."
}
```

- `root_cause.line` is the line the change is about (see stack-to-source). `code` is that line as
  it is in the file now.
- `module`: the build module the file belongs to (`:app`, or an AOSP module name).
- `confidence`: high (the log and the code agree), medium, or low (say what is missing).

**fix.json**: the change as exact replacements, the way an editor makes them:

```json
{
  "summary": "An empty note has no words",
  "changes": [
    {"file": "app/src/main/java/com/example/notes/data/NoteStats.kt",
     "old": "fun wordCount(text: String): Int = text.split(\" \").size",
     "new": "fun wordCount(text: String): Int = text.split(Regex(\"\\\\s+\")).count { it.isNotEmpty() }"},
    {"file": "app/src/test/java/com/example/notes/data/NoteStatsTest.kt",
     "old": "<an anchor that occurs once>", "new": "<the anchor and the new test>"}
  ]
}
```

- `old` must occur exactly once in the file: include enough lines around it. `{"file", "create"}`
  makes a new file.
- **The smallest change that removes the cause.** Keep the code's style, names and comments. No
  reformatting, renaming or tidying of anything else.
- **A unit test** goes with the fix when the project has a tests folder and the fixed code can run
  on the JVM (no Activity, Context or device). It fails before the fix and passes after it. If the
  fix can't be tested that way, say why in `test`.
- Then `fixkit propose <run>` writes `fix.diff`. Fix what it lists.

**investigation.md**: Gate 1's text, a screen at most:

````markdown
# Fix proposal: <use case title>

**Cause:** <cause>

| | |
|---|---|
| Failure | <triage class and summary>, <k> of <n> runs |
| Root cause | `<file>:<line>` in `<function>` |
| Module | :app |
| Test | <the test, or why none> |
| Confidence | high |

<The log lines that show it (5–10), fenced.>

<The code at the root cause (5–10 lines), fenced, with line numbers.>

## The change

```diff
<fix.diff>
```

Then: build with `<build.command>` and run the unit tests with `<build.test>`. Nothing is pushed.
````

## Gate 1 (asked by whoever talks to the user)

Show investigation.md and ask, with three answers:

- **Apply**: apply this change, build it and run the unit tests.
- **Change**: the user says what to change. The investigator revises fix.json, and Gate 1 is asked
  again with the new diff.
- **Stop**: nothing is changed. The investigation stays in the run folder.

Never assume a yes: not from an earlier answer, not from a previous run, not because the change is
small. A subagent can't ask the user, so the gate is asked by the command that runs the agents. If
no one can be asked (a run with nobody there), stop at the gate.

## After an Apply (the fixer)

1. `fixkit apply <run>`. If it refuses, change nothing and say why.
2. `fixkit build <run>`: the build, then the unit tests.
3. `fixkit diff <run>`: `applied.diff`, which must be the same as fix.diff.
4. **If the build or a test fails**, `fixkit undo <run>`, so that the source is as it was, and
   report the errors. A corrected change goes back to the investigator and through Gate 1 again.
   The fixer never edits the source on its own.
5. Write **fix-result.json**:

```json
{
  "run": "runs/…",
  "applied": true,
  "files": ["app/src/main/java/com/example/notes/data/NoteStats.kt", "app/src/test/java/com/example/notes/data/NoteStatsTest.kt"],
  "build": {"ok": true, "seconds": 31.0},
  "tests": {"ok": true, "seconds": 6.2},
  "undone": false,
  "errors": [],
  "next": "Build the app and push it to the device (build-push, Gate 2), then run the use case again."
}
```

The change stays uncommitted: committing is for the user.
