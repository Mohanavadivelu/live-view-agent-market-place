"""The proposed change and its application, for the fix-proposal skill.

    python fixkit.py propose <run folder>   checks fix.json and writes fix.diff (what Gate 1 shows)
    python fixkit.py apply <run folder>     applies fix.json exactly as fix.diff shows it, backing up the files
    python fixkit.py undo <run folder>      puts the backed-up files back
    python fixkit.py build <run folder>     the project's build and unit tests -> build.log, test.log
    python fixkit.py diff <run folder>      the change as applied -> applied.diff

fix.json:
    {"summary": "…", "changes": [
        {"file": "<path from the workspace root>", "old": "<text that occurs once>", "new": "<its replacement>"},
        {"file": "<a new file>", "create": "<its content>"}]}

Changes may touch only the project's source roots and its tests folder. Run from the workspace
root. Prints JSON. Needs Python 3.9+ only.
"""

import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
RUNS = ROOT / "runs"
BACKUP = "backup-src"


def out(obj, code=0):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(message, **more):
    out({"error": message, **more}, 1)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run_folder(run):
    folder = (ROOT / run).resolve()
    if folder.parent != RUNS.resolve() or not folder.is_dir():
        fail(f"{run!r} isn't a run folder (runs/<name>)")
    return folder


def project_for(folder):
    text = (folder / "usecase.txt").read_text(encoding="utf-8") if (folder / "usecase.txt").is_file() else ""
    m = re.search(r"^project:\s*(\S+)\s*$", text, re.M)
    if m:
        project = read_json(ROOT / "projects" / f"{m.group(1)}.json")
    else:
        candidates = [c for c in sorted((ROOT / "projects").glob("*.json")) if c.name != "schema.json"]
        project = read_json(candidates[0]) if len(candidates) == 1 else None
    if not project or not project.get("source_roots"):
        fail("no project with source_roots for this run (projects/<name>.json)")
    return project


def read_text(path):
    # newline="" keeps the file's own line endings, so a change doesn't rewrite the whole file
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def allowed_roots(project):
    roots = list(project["source_roots"]) + ([project["tests"]] if project.get("tests") else [])
    return [(ROOT / r).resolve() for r in roots]


def plan(folder, project):
    """fix.json -> [(path, before or None, after)], or the problems."""
    fix = read_json(folder / "fix.json")
    if fix is None:
        fail("no fix.json in the run folder, or it isn't valid JSON")
    changes, problems = fix.get("changes") or [], []
    if not changes:
        problems.append("fix.json has no changes")
    roots = allowed_roots(project)
    files = {}
    for i, c in enumerate(changes, 1):
        name = c.get("file")
        if not name:
            problems.append(f"change {i}: no file")
            continue
        path = (ROOT / name).resolve()
        if not any(path == r or r in path.parents for r in roots):
            problems.append(f"change {i}: {name} is outside the source roots and the tests folder")
            continue
        if "create" in c:
            if path.exists() or path in files:
                problems.append(f"change {i}: {name} already exists: change it with old/new instead")
                continue
            files[path] = [None, c["create"]]
            continue
        if path not in files:
            if not path.is_file():
                problems.append(f"change {i}: no file {name}")
                continue
            text = read_text(path)
            files[path] = [text, text]
        old, new = c.get("old"), c.get("new")
        if not old or new is None:
            problems.append(f"change {i}: needs old and new (or create)")
            continue
        current = files[path][1]
        # The model writes \n; match the file's own line endings.
        if "\r\n" in current and "\r\n" not in old:
            old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
        count = current.count(old)
        if count != 1:
            problems.append(f"change {i}: the old text occurs {count} times in {name} (it must occur once)")
            continue
        files[path][1] = current.replace(old, new)
    return fix, files, problems


def unified(files):
    parts = []
    for path, (before, after) in files.items():
        name = path.relative_to(ROOT.resolve()).as_posix()
        a = (before or "").replace("\r\n", "\n").splitlines(keepends=True)
        b = after.replace("\r\n", "\n").splitlines(keepends=True)
        diff = difflib.unified_diff(a, b, "/dev/null" if before is None else f"a/{name}", f"b/{name}", n=3)
        parts.append("".join(line if line.endswith("\n") else line + "\n" for line in diff))
    return "".join(parts)


def propose(run):
    folder = run_folder(run)
    fix, files, problems = plan(folder, project_for(folder))
    if problems:
        fail("fix.json can't be applied as it is", problems=problems)
    diff = unified(files)
    (folder / "fix.diff").write_text(diff, encoding="utf-8")
    out({"fix.diff": (folder / "fix.diff").relative_to(ROOT).as_posix(), "summary": fix.get("summary"),
         "files": [p.relative_to(ROOT.resolve()).as_posix() for p in files],
         "added": sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")),
         "removed": sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))})


def apply(run):
    folder = run_folder(run)
    backup = folder / BACKUP
    if (backup / "manifest.json").is_file():
        fail("a change from this run is already applied: undo it first")
    fix, files, problems = plan(folder, project_for(folder))
    if problems:
        fail("fix.json can't be applied as it is", problems=problems)
    shown = (folder / "fix.diff").read_text(encoding="utf-8") if (folder / "fix.diff").is_file() else None
    if shown != unified(files):
        fail("fix.diff isn't what fix.json would change now: run propose and ask Gate 1 again")
    manifest = []
    for path, (before, after) in files.items():
        rel = path.relative_to(ROOT.resolve()).as_posix()
        if before is not None:
            write_text(backup / rel, before)
        manifest.append({"file": rel, "created": before is None})
    backup.mkdir(exist_ok=True)
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for path, (before, after) in files.items():
        write_text(path, after)
    out({"applied": [m["file"] for m in manifest], "backup": (backup).relative_to(ROOT).as_posix()})


def undo(run):
    folder = run_folder(run)
    backup = folder / BACKUP
    manifest = read_json(backup / "manifest.json")
    if manifest is None:
        fail("nothing to undo: no backup-src/manifest.json in this run")
    restored = []
    for m in manifest:
        path = ROOT / m["file"]
        if m["created"]:
            if path.is_file():
                path.unlink()
        else:
            write_text(path, read_text(backup / m["file"]))
        restored.append(m["file"])
    shutil.rmtree(backup)
    out({"restored": restored})


def run_step(command, cwd, env, timeout, log):
    # "gradlew.bat …" means the one in cwd; Windows may not look there (NoDefaultCurrentDirectoryInExePath).
    first, _, rest = command.partition(" ")
    if (cwd / first).is_file():
        command = f'"{(cwd / first).resolve()}" {rest}'.strip()
    started = time.time()
    try:
        p = subprocess.run(command, cwd=cwd, env=env, shell=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        code, text = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        code, text = -1, f"{e.stdout or ''}{e.stderr or ''}\n(stopped after {timeout} s)"
    log.write_text(text, encoding="utf-8")
    errors = [l.strip() for l in text.splitlines()
              if re.match(r"^(e: |error:|.*: error:|FAILURE:|.*FAILED$|\S+Test > \S+ FAILED)", l.strip())]
    return {"ok": code == 0, "exit": code, "seconds": round(time.time() - started, 1),
            "log": log.relative_to(ROOT).as_posix(), "errors": errors[:20],
            "tail": text.strip().splitlines()[-12:] if code != 0 else []}


def build(run):
    folder = run_folder(run)
    project = project_for(folder)
    b = project.get("build")
    if not b or not b.get("command"):
        fail("the project has no build command (projects/<name>.json → build.command)")
    env = dict(os.environ, **b.get("env", {}))
    cwd = ROOT / b.get("cwd", ".")
    timeout = b.get("timeout_s", 1800)
    result = {"build": run_step(b["command"], cwd, env, timeout, folder / "build.log")}
    if b.get("test"):
        result["test"] = run_step(b["test"], cwd, env, timeout, folder / "test.log") if result["build"]["ok"] \
            else {"ok": False, "skipped": "the build failed"}
    result["ok"] = all(step.get("ok") for step in result.values())
    (folder / "build-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    out(result, 0 if result["ok"] else 1)


def diff(run):
    folder = run_folder(run)
    manifest = read_json(folder / BACKUP / "manifest.json")
    if manifest is None:
        fail("nothing applied: no backup-src/manifest.json in this run")
    files = {}
    for m in manifest:
        path = (ROOT / m["file"]).resolve()
        before = None if m["created"] else read_text(folder / BACKUP / m["file"])
        files[path] = [before, read_text(path) if path.is_file() else ""]
    text = unified(files)
    (folder / "applied.diff").write_text(text, encoding="utf-8")
    shown = (folder / "fix.diff").read_text(encoding="utf-8") if (folder / "fix.diff").is_file() else None
    out({"applied.diff": (folder / "applied.diff").relative_to(ROOT).as_posix(), "same_as_fix_diff": text == shown})


def main(argv):
    commands = {"propose": propose, "apply": apply, "undo": undo, "build": build, "diff": diff}
    if len(argv) == 2 and argv[0] in commands:
        return commands[argv[0]](argv[1])
    fail("usage: fixkit.py propose|apply|undo|build|diff <run folder>")


if __name__ == "__main__":
    main(sys.argv[1:])
