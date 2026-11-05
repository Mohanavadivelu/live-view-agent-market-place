---
name: build-module
description: How to build what a project pushes and list it for Gate 2. It runs the project's build command and lists each built file with its device path, sha256 and size in artifacts.json, and warns about a file older than the latest source. Uses the buildkit.py helper. Use when a fix must be built for pushing, or when a push needs its build files.
---

# Building for a push

```
python "${CLAUDE_SKILL_DIR}/scripts/buildkit.py" build <run folder> [--project NAME]
```

Run it from the workspace root, one plain call. It runs the project's `build.command` in `build.cwd`
and writes two files into the run folder:

- **build.log**: everything the build printed.
- **artifacts.json**: `ok`, the time it took and, for each of `push.files`, the `local` path, the
  `device` path, `sha256` and `size`.

`--project` names the config when it isn't the use case's own, such as the same app pushed in
another mode.

buildkit fails if a file is missing, even when the build's exit code is 0. A file older than the
newest file in `source_roots` is a warning, which Gate 2 shows: a build tool leaves a file alone
when the source's content is what it last built from (a fix undone and applied again), so this
doesn't always mean that the change is missing.

## When the build fails

Give the errors from `errors` and `tail`, and the log's path. Don't change the source and don't
retry with other options: a corrected change goes back through code-fix and Gate 1. If the build
can't run at all (no SDK, no JDK, no network for a first download), say what is missing.

The unit tests are not run again here: fixkit ran them after the fix (`build-result.json`), and Gate
2 shows that result.
