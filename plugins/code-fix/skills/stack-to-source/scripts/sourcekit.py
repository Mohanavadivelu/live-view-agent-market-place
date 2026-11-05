"""From a triaged run to the source, for the stack-to-source skill.

    python sourcekit.py resolve <run folder>   the run's app frames and log tags -> file:line, with the code

Reads triage.json and signals.json (log-triage) and the project's source roots. Run from the
workspace root. Prints JSON. Needs Python 3.9+ only.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
RUNS = ROOT / "runs"
# dev.liveview.testbench.data.SettingsStore$Companion.parseSeconds(SettingsStore.kt:26)
FRAME = re.compile(r"^(?:at )?([\w$.]+)\.([\w$<>-]+)\(([\w$.-]+)(?::(\d+))?\)$")
CONTEXT = 4


def out(obj, code=0):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(message):
    out({"error": message}, 1)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def project_for(folder):
    text = (folder / "usecase.txt").read_text(encoding="utf-8") if (folder / "usecase.txt").is_file() else ""
    m = re.search(r"^project:\s*(\S+)\s*$", text, re.M)
    if m:
        return read_json(ROOT / "projects" / f"{m.group(1)}.json")
    candidates = [c for c in sorted((ROOT / "projects").glob("*.json")) if c.name != "schema.json"]
    return read_json(candidates[0]) if len(candidates) == 1 else None


def source_files(roots):
    files = []
    for root in roots:
        files.extend(p for p in (ROOT / root).rglob("*") if p.is_file())
    return files


def snippet(path, line):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    lo, hi = max(1, line - CONTEXT), min(len(lines), line + CONTEXT)
    return [f"{n:>4}{'>' if n == line else ' '} {lines[n - 1]}" for n in range(lo, hi + 1)]


def resolve_frame(frame, files):
    m = FRAME.match(frame.strip())
    if not m:
        return {"frame": frame, "found": False, "why": "not a Java/Kotlin frame"}
    cls, method, file_name, line = m.group(1), m.group(2), m.group(3), m.group(4)
    outer = cls.split("$")[0]
    package_dir = "/".join(outer.split(".")[:-1])
    named = [f for f in files if f.name == file_name]
    # The file is in the folder of its package; Kotlin allows another folder, so fall back to the name.
    exact = [f for f in named if f.parent.as_posix().endswith("/" + package_dir)]
    hits = exact or named
    result = {"frame": frame, "class": cls, "method": method, "line": int(line) if line else None}
    if "$$" in file_name or "$$" in cls:
        result.update(found=False, why="a class the compiler made (a lambda): the frames next to it say where")
        return result
    if not hits:
        result.update(found=False, why=f"no {file_name} in the source roots (a library or the platform?)")
        return result
    path = hits[0]
    result.update(found=True, file=path.relative_to(ROOT).as_posix())
    if len(hits) > 1:
        result["other_files"] = [h.relative_to(ROOT).as_posix() for h in hits[1:]]
    if line:
        result["code"] = snippet(path, int(line))
    return result


def find_tag(tag, files):
    """Where a log tag is defined or used as a literal: "Settings" in TAG = "Settings" or Log.e("Settings", …)."""
    hits = []
    literal = f'"{tag}"'
    for f in files:
        if f.suffix not in (".kt", ".java"):
            continue
        for n, text in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if literal in text:
                hits.append({"file": f.relative_to(ROOT).as_posix(), "line": n, "text": text.strip()[:160]})
    return hits[:10]


def resolve(run):
    folder = (ROOT / run).resolve()
    if folder.parent != RUNS.resolve() or not folder.is_dir():
        fail(f"{run!r} isn't a run folder (runs/<name>)")
    project = project_for(folder)
    if not project or not project.get("source_roots"):
        fail("no project with source_roots for this run (projects/<name>.json)")
    triage = read_json(folder / "triage.json")
    if triage is None:
        fail("no triage.json: triage the run first (log-triage)")
    signals = read_json(folder / "signals.json") or {}
    files = source_files(project["source_roots"] + ([project["tests"]] if project.get("tests") else []))

    frames = list(triage.get("frames") or [])
    for sig in signals.get("signatures", []):
        frames += [f for f in sig.get("owner_frames", []) if f not in frames]
    for err in signals.get("app_errors", []):
        frames += [f for f in err.get("owner_frames", []) if f not in frames]
    tags = [e["tag"] for e in signals.get("app_errors", [])]

    out({
        "run": folder.relative_to(ROOT).as_posix(),
        "class": triage.get("class"),
        "signature": triage.get("signature"),
        "source_roots": project["source_roots"],
        "tests": project.get("tests"),
        "frames": [resolve_frame(f, files) for f in frames[:15]],
        "tags": {t: find_tag(t, files) for t in tags[:5]},
    })


def main(argv):
    if len(argv) == 2 and argv[0] == "resolve":
        return resolve(argv[1])
    fail("usage: sourcekit.py resolve <run folder>")


if __name__ == "__main__":
    main(sys.argv[1:])
