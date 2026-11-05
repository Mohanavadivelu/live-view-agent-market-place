---
name: stack-to-source
description: How to get from a failure in an Android log to the code that causes it. It covers Java and Kotlin stack frames to file:line (inner classes, companions, lambdas, compiler-made classes), a log tag or a string on screen to its source, obfuscated frames with R8 retrace, native frames with ndk-stack or addr2line, and an AOSP module from module-info.json. It then follows the bad value back to where it is made. Use when a triaged run must be traced to its root cause in the source.
---

# From the log to the source

Start from the run's `triage.json` (log-triage): its `frames`, `signature` and evidence. The source
is in the project's `source_roots` (`projects/<name>.json`); the unit tests are in `tests`.

```
python "${CLAUDE_SKILL_DIR}/scripts/sourcekit.py" resolve <run folder>
```

Run it from the workspace root, one plain call. It prints each app frame from the triage and the
log as a file:line with the code around it, and where each of the app's error tags is used.

## Java and Kotlin frames

`at com.example.notes.data.NoteStats$Companion.wordCount(NoteStats.kt:12)`

- The file is the name in brackets, in the folder of the package (`com/example/notes/data/`).
  Kotlin allows another folder, so if it isn't there, look for the name anywhere in the roots.
- `Outer$Inner`, `Outer$Companion`: the same file as `Outer`. `onCreate$lambda$3`: a lambda inside
  `onCreate`. `access$…`, `-$$Nest$…`: a call made through a generated accessor; the real code is
  the method it names.
- `D8$$SyntheticClass`, `$$ExternalSynthetic…`: classes the compiler made. They have no source:
  the frames next to them say where.
- A line past the end of a Kotlin file belongs to an **inline** function: the code is in the
  function inlined there (often a library one), called from the nearest frame with a real line.
- **Obfuscated frames** (`a.b.c(Unknown Source:12)`): retrace them with the build's
  `mapping.txt` (`build/outputs/mapping/<variant>/mapping.txt`): `retrace mapping.txt stack.txt`
  (Android SDK `cmdline-tools/latest/bin/retrace`).

## Native frames

```
#00 pc 000000000004f2a8  /system/lib64/libfoo.so (Foo::bar(int)+40)
```

- Symbols come from the build that made the library: `out/target/product/<device>/symbols/…` in
  AOSP, the unstripped libraries under `build/intermediates/merged_native_libs/` in an app.
- `ndk-stack -sym <symbols dir> -i tombstone.txt` resolves a whole tombstone;
  `llvm-addr2line -Cfie <unstripped .so> 0x4f2a8` resolves one pc.
- The library's module: AOSP's `out/target/product/<device>/module-info.json` maps each module
  to its `path` (the source folder) and `installed` (the files on the device). Search it for the
  library's file name.

## No stack: tags, text and timings

- **A log tag**: `sourcekit` lists where the tag is used. The line with the message text is where
  it is logged.
- **Text on screen** (a wrong-screen failure): search the resources for the text the screen showed
  (`res/values*/strings.xml`), then the code for its name (`R.string.<name>`, `@string/<name>`).
  A typo in a string is fixed in the resource, in every language folder that has it.
- **Slow**: the app's own timing line, if it has one, says what was measured. Read the code between
  the log lines around the wait, and look for work that is repeated more than it needs to be, or
  that waits: I/O, a query, a sleep, a lock.
- **ANR**: the main thread was blocked. Find what the frozen screen's code calls on the main thread
  (a click handler, `onCreate`, `onResume`) that waits: `poll`, `take`, `get`, `join`, `sleep`, a
  lock, I/O or a network call.
- **Flaky**: look for what can differ between runs: state shared between threads, code that
  depends on which of two things finishes first, timeouts, and the device's own state.

## The root cause

The frame where it fails is where to start, not always where to change. Read the function, then
follow the bad value back:

- Where is the null, the wrong string or the wrong path made? Which caller passes it?
- The **root cause line** is the line to change: the one that makes or lets in the wrong value. If
  a null is a valid answer (no network), the missing check is added where the value is used.
- Give one line, plus `also` for other lines that are part of the same cause (a blocking call, and
  the main-thread caller that makes it a problem).
- Check it against the log: does the cause explain every line of the signature, the timing and
  the steps of the use case? If it doesn't, say so.
