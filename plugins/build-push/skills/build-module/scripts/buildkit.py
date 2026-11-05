"""Builds what a project pushes and lists it, for the build-module skill.

    python buildkit.py build <run folder> [--project NAME]

Runs the project's build.command, then lists each push file: local path, device path, sha256, size.
It writes build.log and artifacts.json into the run folder. A missing file is an error, and a file
older than the newest source file is a warning that Gate 2 shows.

Run from the workspace root. Prints JSON. Needs Python 3.9+ only.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
RUNS = ROOT / "runs"


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


def project_for(folder, name):
    if not name:
        text = (folder / "usecase.txt").read_text(encoding="utf-8") if (folder / "usecase.txt").is_file() else ""
        m = re.search(r"^project:\s*(\S+)\s*$", text, re.M)
        name = m.group(1) if m else None
    if not name:
        fail("the run names no project: give --project <name>")
    project = read_json(ROOT / "projects" / f"{name}.json")
    if not project:
        fail(f"no project config projects/{name}.json")
    return project


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def newest_source(project):
    newest, name = 0, None
    for root in project.get("source_roots", []):
        for folder, dirs, files in os.walk(ROOT / root):
            dirs[:] = [d for d in dirs if d not in (".git", "build", "out")]
            for f in files:
                path = Path(folder) / f
                when = path.stat().st_mtime
                if when > newest:
                    newest, name = when, path
    return newest, name


def build(run, project_name):
    folder = run_folder(run)
    project = project_for(folder, project_name)
    b, push = project.get("build"), project.get("push")
    if not b or not b.get("command"):
        fail("the project has no build command (projects/<name>.json → build.command)")
    if not push or not push.get("files"):
        fail("the project has no files to push (projects/<name>.json → push.files)")

    cwd = ROOT / b.get("cwd", ".")
    # "gradlew.bat …" means the one in cwd; Windows may not look there (NoDefaultCurrentDirectoryInExePath).
    command = b["command"]
    first, _, rest = command.partition(" ")
    if (cwd / first).is_file():
        command = f'"{(cwd / first).resolve()}" {rest}'.strip()
    started = time.time()
    timeout = b.get("timeout_s", 1800)
    try:
        p = subprocess.run(command, cwd=cwd, env=dict(os.environ, **b.get("env", {})), shell=True,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        code, text = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        code, text = -1, f"{e.stdout or ''}{e.stderr or ''}\n(stopped after {timeout} s)"
    (folder / "build.log").write_text(text, encoding="utf-8")
    result = {"project": project["name"], "command": b["command"], "ok": code == 0, "exit": code,
              "seconds": round(time.time() - started, 1), "log": (folder / "build.log").relative_to(ROOT).as_posix()}

    if code != 0:
        result["errors"] = [l.strip() for l in text.splitlines()
                            if re.match(r"^(e: |error:|.*: error:|FAILURE:|.*FAILED$|ninja: )", l.strip())][:20]
        result["tail"] = text.strip().splitlines()[-12:]
    else:
        newest, newest_name = newest_source(project)
        result["files"], problems, warnings = [], [], []
        for f in push["files"]:
            local = ROOT / f["local"]
            if not local.is_file():
                problems.append(f"the build didn't make {f['local']}")
                continue
            # Only a warning: a build tool leaves a file alone when the source's content is what it last built from.
            if local.stat().st_mtime < newest:
                warnings.append(f"{f['local']} is older than {newest_name.relative_to(ROOT).as_posix()}: "
                                "the build tool didn't remake it")
            result["files"].append(dict(f, sha256=sha256(local), size=local.stat().st_size))
        if problems:
            result["ok"], result["errors"] = False, problems
        if warnings:
            result["warnings"] = warnings
    (folder / "artifacts.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out(result, 0 if result["ok"] else 1)


def main(argv):
    project = None
    if "--project" in argv:
        i = argv.index("--project")
        project = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    if len(argv) == 2 and argv[0] == "build":
        return build(argv[1], project)
    fail("usage: buildkit.py build <run folder> [--project NAME]")


if __name__ == "__main__":
    main(sys.argv[1:])
