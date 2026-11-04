"""The mechanical parts of a use case run, for the run-procedure skill.

    python runkit.py start <usecase.txt> [--serial S]   run folder, lock, device.json, replay source
    python runkit.py adb <serial> <adb arguments…>       adb -s <serial> …, found without PATH
    python runkit.py seq <serial> "tap X Y" "wait 2" "key BACK" …  a timed sequence in one adb call
    python runkit.py wait <seconds>
    python runkit.py since <run folder>                  seconds since the run started (for since_seconds)
    python runkit.py collect <run folder> <file> [<name>]  copy a file (from anywhere) into the run
    python runkit.py restore <run folder>                Bluetooth / Wi-Fi / airplane as in device.json
    python runkit.py finish <run folder>                 check the files, release the lock

Run from the workspace root (runs/, projects/ and usecases/ are there). Prints JSON, except `adb`,
which prints adb's output and exits with its code. Needs Python 3.9+ and nothing else.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
RUNS = ROOT / "runs"
LOCKS = RUNS / ".locks"
RUN_FILES = ["usecase.txt", "device.json", "steps.json", "result.json", "logcat.log", "screen.mp4"]
# Git Bash turns /data/local/tmp into C:/Program Files/Git/data/local/tmp before we see it.
GIT_BASH_PATH = re.compile(r"^[A-Za-z]:/Program Files/Git(/.*)$")


def out(obj, code=0):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(message, **more):
    out({"error": message, **more}, 1)


def adb_path():
    found = shutil.which("adb")
    if found:
        return found
    for var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        home = os.environ.get(var)
        if home:
            for name in ("adb.exe", "adb"):
                candidate = Path(home) / "platform-tools" / name
                if candidate.is_file():
                    return str(candidate)
    fail("adb not found: put it on PATH or set ANDROID_HOME")


def adb(serial, *args, timeout=60):
    args = [GIT_BASH_PATH.sub(r"\1", a) for a in args]
    cmd = [adb_path()] + (["-s", serial] if serial else []) + list(args)
    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, creationflags=flags)
    return p.returncode, (p.stdout + p.stderr).strip()


def shell(serial, command):
    return adb(serial, "shell", command)[1]


def now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def find_project(text):
    m = re.search(r"^project:\s*(\S+)\s*$", text, re.M)
    if m:
        path = ROOT / "projects" / f"{m.group(1)}.json"
        if not path.is_file():
            fail(f"the use case names project {m.group(1)!r} but {path.relative_to(ROOT)} doesn't exist")
        return path
    candidates = sorted((ROOT / "projects").glob("*.json"))
    candidates = [c for c in candidates if c.name != "schema.json"]
    return candidates[0] if len(candidates) == 1 else None


def pick_serial(wanted):
    code, text = adb(None, "devices")
    online = [l.split("\t")[0] for l in text.splitlines()[1:] if l.endswith("\tdevice")]
    if wanted:
        if wanted not in online:
            fail(f"device {wanted} isn't online", online=online)
        return wanted
    if len(online) != 1:
        fail("name the device: " + ("none is connected" if not online else "several are connected"), online=online)
    return online[0]


def start(usecase, serial_arg):
    path = (ROOT / usecase).resolve()
    if not path.is_file():
        fail(f"no use case at {usecase}")
    text = path.read_text(encoding="utf-8")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    project_path = find_project(text)
    project = json.loads(project_path.read_text(encoding="utf-8")) if project_path else {}
    serial = pick_serial(serial_arg or project.get("device", {}).get("serial"))

    LOCKS.mkdir(parents=True, exist_ok=True)
    lock = LOCKS / serial
    took_over = None
    if lock.exists():
        held = lock.read_text(encoding="utf-8").splitlines()
        holder = ROOT / held[0] if held else None
        if holder and (holder / "result.json").is_file():
            took_over = held[0]  # that run finished but didn't release the lock
        else:
            fail(f"device {serial} is locked by another run", held_by=held,
                 hint=f"if that run is gone, delete runs/.locks/{serial}")

    stem = path.stem
    run = RUNS / f"{datetime.now():%Y%m%d-%H%M%S}-{stem}"
    run.mkdir(parents=True)
    shutil.copyfile(path, run / "usecase.txt")
    rel = run.relative_to(ROOT).as_posix()
    lock.write_text(f"{rel}\n{now()}\n", encoding="utf-8")

    replay_from = None
    for earlier in sorted(RUNS.glob(f"*-{stem}/steps.json"), reverse=True):
        if earlier.parent == run:
            continue
        try:
            if json.loads(earlier.read_text(encoding="utf-8")).get("usecase_sha256") == sha:
                replay_from = earlier.relative_to(ROOT).as_posix()
                break
        except ValueError:
            continue

    package = project.get("app", {}).get("package")
    props = shell(serial, "getprop ro.product.model; getprop ro.build.version.release; "
                          "getprop ro.build.version.sdk; getprop ro.build.type").splitlines() + [""] * 4
    settings = shell(serial, "settings get global bluetooth_on; settings get global wifi_on; "
                             "settings get global airplane_mode_on").splitlines() + [""] * 3
    version = updated = None
    if package:
        info = shell(serial, f"dumpsys package {package}")
        m = re.search(r"versionName=(\S+)", info)
        version = m.group(1) if m else None
        m = re.search(r"lastUpdateTime=(.+)", info)  # changes on every install: tells builds apart
        updated = m.group(1).strip() if m else None
    device = {
        "serial": serial, "model": props[0], "android": props[1], "sdk": props[2], "build_type": props[3],
        "bluetooth_on": settings[0], "wifi_on": settings[1], "airplane_mode_on": settings[2],
        "package": package, "app_version": version, "app_updated": updated,
        "host_time": now(), "device_time": shell(serial, "date +%Y-%m-%dT%H:%M:%S.%3N%z"),
    }
    (run / "device.json").write_text(json.dumps(device, indent=2) + "\n", encoding="utf-8")
    out({
        "run": rel, "serial": serial, "usecase": path.relative_to(ROOT).as_posix(), "usecase_sha256": sha,
        "project": project_path.stem if project_path else None, "package": package,
        "screens": project.get("app", {}).get("screens", {}), "mode": "replay" if replay_from else "interpret",
        "replay_from": replay_from, "took_over_lock_from": took_over, "device": device,
    })


def run_folder(run):
    folder = (ROOT / run).resolve()
    if folder.parent != RUNS.resolve() or not folder.is_dir():
        fail(f"{run!r} isn't a run folder (runs/<name>)")
    return folder


SEQ_ITEM = re.compile(r"^(tap \d+ \d+|swipe \d+ \d+ \d+ \d+(?: \d+)?|key [A-Z0-9_]+|wait \d+(?:\.\d+)?)$")


def seq(serial, items):
    """Taps, swipes, keys and waits in one adb shell call, timed on the device."""
    script = []
    for i, item in enumerate(items):
        if not SEQ_ITEM.match(item):
            fail(f"not a sequence item: {item!r} (tap X Y | swipe X1 Y1 X2 Y2 [MS] | key NAME | wait S)")
        kind, *args = item.split()
        script.append(f'echo "@{i} $(date +%H:%M:%S.%3N)"')
        if kind == "wait":
            script.append(f"sleep {args[0]}")
        elif kind == "key":
            script.append(f"input keyevent KEYCODE_{args[0].removeprefix('KEYCODE_')}")
        else:
            script.append(f"input {kind} {' '.join(args)}")
    script.append(f'echo "@{len(items)} $(date +%H:%M:%S.%3N)"')
    code, text = adb(serial, "shell", "; ".join(script), timeout=600)
    times = dict(re.findall(r"^@(\d+) (\S+)$", text, re.M))
    done = [{"item": item, "at": times.get(str(i)), "until": times.get(str(i + 1))} for i, item in enumerate(items)]
    out({"exit": code, "steps": done, "other_output": [l for l in text.splitlines() if not l.startswith("@")]},
        0 if code == 0 else 1)


def collect(run, src, name=None):
    run, src = run_folder(run), Path(src)
    if not src.is_file():
        fail(f"no file {src}")
    dest = run / (name or src.name)
    shutil.copyfile(src, dest)
    out({"copied": dest.relative_to(ROOT).as_posix(), "bytes": dest.stat().st_size})


def since(run):
    started = datetime.fromisoformat(json.loads((run_folder(run) / "device.json").read_text(encoding="utf-8"))["host_time"])
    seconds = (datetime.now().astimezone() - started).total_seconds()
    out({"since_seconds": max(1, int(seconds) + 1), "started": started.isoformat()})


def restore(run):
    saved = json.loads((run_folder(run) / "device.json").read_text(encoding="utf-8"))
    serial = saved["serial"]
    current = shell(serial, "settings get global bluetooth_on; settings get global wifi_on; "
                            "settings get global airplane_mode_on").splitlines() + [""] * 3
    commands = {
        "bluetooth_on": ("cmd bluetooth_manager enable", "cmd bluetooth_manager disable"),
        "wifi_on": ("cmd wifi set-wifi-enabled enabled", "cmd wifi set-wifi-enabled disabled"),
        "airplane_mode_on": ("cmd connectivity airplane-mode enable", "cmd connectivity airplane-mode disable"),
    }
    changed = {}
    for (key, (on, off)), value in zip(commands.items(), current):
        want = saved.get(key)
        if want in ("0", "1") and value != want:
            shell(serial, on if want == "1" else off)
            changed[key] = f"{value} -> {want}"
    out({"restored": changed})


def finish(run):
    folder = run_folder(run)
    run = folder.relative_to(ROOT.resolve()).as_posix()
    missing =[f for f in RUN_FILES if not (folder / f).is_file()]
    if not list(folder.glob("*.png")):
        missing.append("screenshots (*.png)")
    released = False
    for lock in LOCKS.glob("*") if LOCKS.is_dir() else []:
        if lock.read_text(encoding="utf-8").splitlines()[:1] == [run]:
            lock.unlink()
            released = True
    out({"run": run, "missing": missing, "lock_released": released})


def main(argv):
    if not argv:
        fail("usage: runkit.py start|adb|seq|wait|since|collect|restore|finish …")
    cmd, args = argv[0], argv[1:]
    if cmd == "start" and args:
        serial = args[args.index("--serial") + 1] if "--serial" in args else None
        return start(args[0], serial)
    if cmd == "adb" and len(args) >= 2:
        code, text = adb(args[0], *args[1:], timeout=600)
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)
        sys.exit(code)
    if cmd == "seq" and len(args) >= 2:
        return seq(args[0], args[1:])
    if cmd == "wait" and len(args) == 1:
        time.sleep(float(args[0]))
        return out({"waited_s": float(args[0])})
    if cmd == "collect" and len(args) in (2, 3):
        return collect(*args)
    if cmd == "since" and len(args) == 1:
        return since(args[0])
    if cmd == "restore" and len(args) == 1:
        return restore(args[0])
    if cmd == "finish" and len(args) == 1:
        return finish(args[0])
    fail(f"don't know: {' '.join(argv)}")


if __name__ == "__main__":
    main(sys.argv[1:])
