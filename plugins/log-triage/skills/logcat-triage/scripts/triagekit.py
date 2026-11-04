"""The mechanical part of triage, for the logcat-triage skill.

    python triagekit.py scan <run folder>    what the run's files show: signatures, the app's errors,
                                             failed steps, earlier runs to compare; saved as signals.json
    python triagekit.py check <run folder>   checks the run's triage.json

Run from the workspace root (runs/ and projects/ are there). Prints JSON. Needs Python 3.9+ only.
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path.cwd()
RUNS = ROOT / "runs"
CLASSES = ["pass", "crash", "native-crash", "anr", "error-dialog", "wrong-screen", "slow", "timeout",
           "log-only", "flaky", "environment"]
# threadtime: 11-04 09:45:32.011 11689 11689 E AndroidRuntime: FATAL EXCEPTION: main
LINE = re.compile(r"^(\d\d-\d\d) (\d\d:\d\d:\d\d\.\d{3})\s+(\d+)\s+(\d+) ([VDIWEFA]) (.*?)\s*: ?(.*)$")
EXCEPTION = re.compile(r"\b((?:[a-z]\w*\.)+[A-Z]\w*(?:Exception|Error))\b")
FRAME = re.compile(r"^\s*at ([\w$.<>]+)\(([^)]*)\)")
MAX_BLOCK = 60


def out(obj, code=0):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(message):
    out({"error": message}, 1)


def run_folder(run):
    folder = (ROOT / run).resolve()
    if folder.parent != RUNS.resolve() or not folder.is_dir():
        fail(f"{run!r} isn't a run folder (runs/<name>)")
    return folder


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def project_for(usecase_text):
    m = re.search(r"^project:\s*(\S+)\s*$", usecase_text, re.M)
    if m:
        return read_json(ROOT / "projects" / f"{m.group(1)}.json") or {}
    candidates = [c for c in sorted((ROOT / "projects").glob("*.json")) if c.name != "schema.json"]
    return (read_json(candidates[0]) or {}) if len(candidates) == 1 else {}


def parse_time(text):
    try:
        return datetime.fromisoformat(re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", text))
    except (TypeError, ValueError):
        return None


class Clock:
    """Logcat times are the device's local time without a year; steps are on the host clock."""

    def __init__(self, device):
        self.device_time = parse_time(device.get("device_time"))
        host = parse_time(device.get("host_time"))
        self.offset = (host - self.device_time).total_seconds() if host and self.device_time else 0.0

    def log_time(self, md, hms):
        if not self.device_time:
            return None
        t = datetime.strptime(f"{self.device_time.year}-{md} {hms}", "%Y-%m-%d %H:%M:%S.%f")
        return t.replace(tzinfo=self.device_time.tzinfo)

    def to_host(self, t):
        return t + timedelta(seconds=self.offset) if t else None


def read_log(path):
    entries = []
    if not path.is_file():
        return entries
    for n, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        m = LINE.match(raw)
        if m:
            md, hms, pid, tid, level, tag, msg = m.groups()
            entries.append({"n": n, "md": md, "hms": hms, "pid": int(pid), "tid": int(tid),
                            "level": level, "tag": tag, "msg": msg})
    return entries


def app_pids(entries, processes):
    """pid -> process name, for the app's processes (name or name:sub)."""
    def ours(name):
        return any(name == p or name.startswith(p + ":") for p in processes)

    pids, anr_process = {}, None
    for e in entries:
        # "Start proc 11689:dev.liveview.testbench/u0a238", "Killing 11689:dev.liveview.testbench/u0a238"
        for m in re.finditer(r"\b(\d+):([\w.:]+)/u\d+", e["msg"]):
            if ours(m.group(2)):
                pids[int(m.group(1))] = m.group(2)
        for pattern in (r"Process: ([\w.:]+), PID: (\d+)", r"Process ([\w.:]+) \(pid (\d+)\) has died"):
            m = re.search(pattern, e["msg"])
            if m and ours(m.group(1)):
                pids[int(m.group(2))] = m.group(1)
        # an ANR report names the pid on a line of its own: "ANR in <process> (…)" … "PID: 13326"
        m = re.match(r"ANR in ([\w.:]+) ", e["msg"])
        if m and ours(m.group(1)):
            anr_process = m.group(1)
        elif anr_process and re.fullmatch(r"PID: \d+", e["msg"].strip()):
            pids[int(e["msg"].split()[1])] = anr_process
            anr_process = None
    return pids


def block(entries, i, same_tag=True):
    """The lines of one report: the same pid (and tag) right after entries[i]."""
    first, lines = entries[i], [entries[i]]
    for e in entries[i + 1:]:
        if e["pid"] != first["pid"] or (same_tag and e["tag"] != first["tag"]) or len(lines) >= MAX_BLOCK:
            break
        lines.append(e)
    return lines


def owner_frames(lines, packages):
    frames = []
    for e in lines:
        m = FRAME.match(e["msg"])
        if m and any(m.group(1).startswith(p + ".") for p in packages):
            frames.append(f"{m.group(1)}({m.group(2)})")
    return frames


def exception_chain(lines):
    """The exception lines (not frames): the first is the outer one, the last 'Caused by' the root."""
    chain = []
    for e in lines:
        msg = e["msg"]
        if FRAME.match(msg) or msg.strip().startswith("..."):
            continue
        if EXCEPTION.search(msg):
            chain.append(msg.strip()[:300])
    return chain


def signatures(entries, pids, processes, packages, clock):
    found = []

    def add(kind, i, lines, process, pid, headline, **more):
        e = entries[i]
        t = clock.log_time(e["md"], e["hms"])
        found.append({
            "kind": kind, "device_time": f"{e['md']} {e['hms']}",
            "host_time": clock.to_host(t).isoformat(timespec="milliseconds") if t else None,
            "process": process, "pid": pid,
            "ours": process is not None and any(process == p or process.startswith(p + ":") for p in processes),
            "headline": headline, "lines": f"{lines[0]['n']}-{lines[-1]['n']}", **more,
        })

    for i, e in enumerate(entries):
        msg = e["msg"]
        if e["tag"] == "AndroidRuntime" and msg.startswith("FATAL EXCEPTION"):
            lines = block(entries, i)
            text = "\n".join(l["msg"] for l in lines)
            m = re.search(r"Process: ([\w.:]+), PID: (\d+)", text)
            chain = exception_chain(lines)
            add("crash", i, lines, m.group(1) if m else pids.get(e["pid"]), int(m.group(2)) if m else e["pid"],
                chain[0] if chain else msg, exceptions=chain, root=chain[-1] if chain else None,
                owner_frames=owner_frames(lines, packages)[:10])
        elif msg.startswith("ANR in "):
            lines = block(entries, i)
            text = "\n".join(l["msg"] for l in lines)
            # WindowManager also says "ANR in Window{668a05 u0 <package>/<activity>}"
            m = re.search(r"ANR in Window\{\w+ u\d+ ([\w.:]+)/", msg) or re.search(r"ANR in ([\w.:]+)", msg)
            pid = re.search(r"^PID: (\d+)", text, re.M)
            reason = re.search(r"^Reason: (.*)$", text, re.M)
            add("anr", i, lines, m.group(1) if m else None, int(pid.group(1)) if pid else None,
                msg, reason=reason.group(1)[:300] if reason else None)
        elif re.search(r"Fatal signal \d+ \(SIG\w+\)", msg):
            m = re.search(r"Fatal signal \d+ \((SIG\w+)\).*?pid (\d+) \(([^)]*)\)", msg)
            pid = int(m.group(2)) if m else e["pid"]
            add("native-crash", i, block(entries, i), pids.get(pid) or (m.group(3) if m else None), pid,
                msg[:300], signal=m.group(1) if m else None)
        elif e["tag"] == "DEBUG" and ">>> " in msg and " <<<" in msg:
            m = re.search(r"pid: (\d+).*>>> ([^ ]+) <<<", msg)
            lines = block(entries, i)
            frames = [l["msg"].strip() for l in lines if re.match(r"\s*#\d\d pc", l["msg"])]
            add("tombstone", i, lines, m.group(2) if m else None, int(m.group(1)) if m else None, msg[:300],
                backtrace=frames[:12])
        elif "WATCHDOG KILLING SYSTEM PROCESS" in msg:
            add("watchdog", i, block(entries, i), "system_server", e["pid"], msg[:300])
        elif re.search(r"Process ([\w.:]+) \(pid (\d+)\) has died", msg):
            m = re.search(r"Process ([\w.:]+) \(pid (\d+)\) has died", msg)
            if any(m.group(1) == p or m.group(1).startswith(p + ":") for p in processes):
                add("process-died", i, [e], m.group(1), int(m.group(2)), msg[:300])
        elif re.search(r"lmkd|lowmemorykiller", e["tag"]) and any(p in msg for p in processes):
            add("low-memory-kill", i, [e], next((p for p in processes if p in msg), None), None, msg[:300])
        elif "DeadObjectException" in msg and e["level"] in "EWF" and e["pid"] in pids:
            add("dead-object", i, block(entries, i), pids.get(e["pid"]), e["pid"], msg[:300])
    # One ANR is reported by WindowManager and by ActivityManager: keep ActivityManager's (it has the pid).
    full = {(s["process"]) for s in found if s["kind"] == "anr" and not s["headline"].startswith("ANR in Window")}
    return [s for s in found if not (s["kind"] == "anr" and s["headline"].startswith("ANR in Window")
                                     and s["process"] in full)]


def app_errors(entries, pids, packages):
    """The app's E and F lines, grouped by tag."""
    groups = {}
    for i, e in enumerate(entries):
        if e["pid"] not in pids or e["level"] not in "EF" or e["tag"] == "AndroidRuntime":
            continue
        g = groups.setdefault(e["tag"], {"tag": e["tag"], "count": 0, "first": f"{e['md']} {e['hms']}",
                                         "first_line": e["n"], "first_message": e["msg"][:300],
                                         "exceptions": {}, "owner_frames": []})
        g["count"] += 1
        g["last"] = f"{e['md']} {e['hms']}"
        for x in EXCEPTION.findall(e["msg"]):
            g["exceptions"][x] = g["exceptions"].get(x, 0) + 1
        m = FRAME.match(e["msg"])
        if m and any(m.group(1).startswith(p + ".") for p in packages):
            frame = f"{m.group(1)}({m.group(2)})"
            if frame not in g["owner_frames"] and len(g["owner_frames"]) < 6:
                g["owner_frames"].append(frame)
    # A stack trace is many lines; count the reports too (lines that aren't frames or "Caused by").
    for g in groups.values():
        g["reports"] = sum(1 for e in entries if e["pid"] in pids and e["tag"] == g["tag"] and e["level"] in "EF"
                           and not FRAME.match(e["msg"]) and not e["msg"].lstrip().startswith(("Caused by", "...")))
    return sorted(groups.values(), key=lambda g: -g["count"])


def timings(entries, pids):
    """The app's own measurements ("after 5088 ms"): often the best evidence for a slow step."""
    found = []
    for e in entries:
        if e["pid"] in pids and e["level"] in "IDW" and not e["msg"].startswith("Davey!") and re.search(r"\b\d+(?:\.\d+)? ?ms\b", e["msg"]):
            found.append({"line": e["n"], "device_time": f"{e['md']} {e['hms']}", "tag": e["tag"], "message": e["msg"][:200]})
    return found[:15]


def crash_files(folder):
    files = []
    for f in sorted(folder.glob("crash-*.txt")):
        head = f.read_text(encoding="utf-8", errors="replace").splitlines()[:40]
        fields = {}
        for l in head:
            m = re.match(r"^(Process|PID|Subject|Activity|Timestamp|Package|Foreground|Build|Cmd line|Abort message|signal \d+.*?):\s*(.*)$", l)
            if m and m.group(1) not in fields:
                fields[m.group(1)] = m.group(2)[:200]
        files.append({"file": f.name, "bytes": f.stat().st_size, **fields})
    return files


def usecase_sha(folder):
    path = folder / "usecase.txt"
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest() if path.is_file() else None


def failed_checks(result):
    return [{"n": s.get("n"), "line": s.get("line"), "status": s.get("status"), "evidence": s.get("evidence")}
            for s in (result or {}).get("steps", []) if s.get("status") in ("fail", "failed")]


def comparable_runs(folder, device):
    """Other runs of the same, unchanged use case on the same build of the app."""
    sha = usecase_sha(folder)
    runs = []
    for other in sorted(RUNS.iterdir()):
        if not other.is_dir() or other == folder or other.name.startswith(".") or usecase_sha(other) != sha:
            continue
        result = read_json(other / "result.json")
        if not result:
            continue
        theirs = read_json(other / "device.json") or {}
        same = None
        if device.get("app_updated") and theirs.get("app_updated"):
            same = device["app_updated"] == theirs["app_updated"]
        elif device.get("app_version") != theirs.get("app_version"):
            same = False
        if same is False:
            continue
        runs.append({"run": other.relative_to(ROOT).as_posix(), "verdict": result.get("verdict"),
                     "same_build": same, "failed": [c["line"] for c in failed_checks(result)],
                     "triaged": (other / "triage.json").is_file()})
    return runs


def steps_on_host(result):
    steps = []
    for s in (result or {}).get("steps", []):
        steps.append({"n": s.get("n"), "line": s.get("line"), "status": s.get("status"),
                      "start": s.get("start"), "end": s.get("end")})
    return steps


def step_at(steps, host_time):
    t = parse_time(host_time)
    if not t:
        return None
    last = None
    for s in steps:
        start = parse_time(s.get("start"))
        if start and start <= t + timedelta(seconds=1):
            last = s["n"]
    return last


def scan(run):
    folder = run_folder(run)
    usecase = (folder / "usecase.txt").read_text(encoding="utf-8") if (folder / "usecase.txt").is_file() else ""
    project = project_for(usecase)
    device = read_json(folder / "device.json") or {}
    result = read_json(folder / "result.json")
    package = device.get("package") or project.get("app", {}).get("package")
    owner = project.get("owner", {})
    processes = owner.get("processes") or ([package] if package else [])
    packages = owner.get("packages") or ([package] if package else [])

    clock = Clock(device)
    entries = read_log(folder / "logcat.log")
    pids = app_pids(entries, processes)
    sigs = signatures(entries, pids, processes, packages, clock)
    steps = steps_on_host(result)
    for s in sigs:
        s["step"] = step_at(steps, s["host_time"])
    repeat = re.search(r"^repeat:\s*(\d+)\s*$", usecase, re.M)

    signals = {
        "run": folder.relative_to(ROOT).as_posix(),
        "usecase": (result or {}).get("usecase"),
        "title": next((l.lstrip("# ").strip() for l in usecase.splitlines() if l.startswith("#")), None),
        "repeat": int(repeat.group(1)) if repeat else 1,
        "verdict": (result or {}).get("verdict"),
        "failed": failed_checks(result),
        "unexpected": (result or {}).get("unexpected", []),
        "steps": steps,
        "owner": {"processes": processes, "packages": packages, "pids": {str(k): v for k, v in pids.items()}},
        "clock": {"host_minus_device_s": round(clock.offset, 3),
                  "note": "logcat times are device time; host time = device time + host_minus_device_s"},
        "signatures": sigs,
        "app_errors": app_errors(entries, pids, packages),
        "app_timings": timings(entries, pids),
        "crash_files": crash_files(folder),
        "comparable_runs": comparable_runs(folder, device),
        "files": sorted(f.name for f in folder.iterdir() if f.is_file()),
        "log_lines": len(entries),
    }
    if not result:
        signals["problems"] = ["no result.json: the run didn't finish"]
    if not entries:
        signals.setdefault("problems", []).append("no logcat.log, or it is empty")
    (folder / "signals.json").write_text(json.dumps(signals, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out(signals)


def check(run):
    folder = run_folder(run)
    triage = read_json(folder / "triage.json")
    if triage is None:
        fail("no triage.json, or it isn't valid JSON")
    problems = []
    for key in ("class", "ours", "summary", "evidence", "repro"):
        if key not in triage:
            problems.append(f"missing {key}")
    if triage.get("class") not in CLASSES:
        problems.append(f"class must be one of {', '.join(CLASSES)}")
    if triage.get("ours") not in (True, False, "unknown"):
        problems.append("ours must be true, false or \"unknown\"")
    repro = triage.get("repro") or {}
    if not isinstance(repro.get("failed"), int) or not isinstance(repro.get("runs"), int):
        problems.append("repro needs failed and runs (numbers)")
    for ev in triage.get("evidence") or []:
        name = ev.get("file") if isinstance(ev, dict) else None
        if not name or not (folder / name).is_file() and not (ROOT / name).is_file():
            problems.append(f"evidence file not found: {name}")
    if not (folder / "triage.md").is_file():
        problems.append("no triage.md")
    out({"run": folder.relative_to(ROOT).as_posix(), "ok": not problems, "problems": problems},
        0 if not problems else 1)


def main(argv):
    if len(argv) == 2 and argv[0] == "scan":
        return scan(argv[1])
    if len(argv) == 2 and argv[0] == "check":
        return check(argv[1])
    fail("usage: triagekit.py scan <run folder> | check <run folder>")


if __name__ == "__main__":
    main(sys.argv[1:])
