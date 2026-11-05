"""Pushes a build to a device and takes it back, for the adb-push-deploy skill.

    python pushkit.py plan <run folder> [--project NAME] [--serial S]   push-plan.json, push-plan.md (Gate 2's text)
    python pushkit.py push <run folder> [--reboot]                      backup, push, checksums, restart, checks
    python pushkit.py status <run folder>                               what is on the device now, against the backup
    python pushkit.py rollback <run folder> [--force]                   puts the backup back

`plan` only reads from the device. `push` does exactly what the plan says, and refuses if the
files, the project config or the device are no longer what the plan shows. If a step or a check
fails, `push` puts the backup back by itself. It writes push-result.json.

Run from the workspace root. Prints JSON. Needs Python 3.9+ and adb (PATH or ANDROID_HOME).
"""

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path, PurePosixPath

ROOT = Path.cwd()
RUNS = ROOT / "runs"
LOCKS = RUNS / ".locks"
BACKUP = "backup"
BOOT_TIMEOUT = 300
UNLOCK_TIMEOUT = 60
# The device-safety skill's "never": a project config can't ask for these either.
FORBIDDEN = re.compile(r"fastboot|bootloader|recovery|wipe|MASTER_CLEAR|\brm\s+-\w*r|\bpm\s+clear\b|"
                       r"\bmkfs\b|\bdd\s", re.I)


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


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


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


def adb(serial, *args, timeout=120):
    cmd = [adb_path()] + (["-s", serial] if serial else []) + [str(a) for a in args]
    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, creationflags=flags)
        return p.returncode, (p.stdout + p.stderr).strip().replace("\r\n", "\n")
    except subprocess.TimeoutExpired:
        return -1, f"adb {' '.join(str(a) for a in args)}: no answer after {timeout} s"


def shell(serial, command, timeout=120):
    return adb(serial, "shell", command, timeout=timeout)


def getprop(serial, name):
    return shell(serial, f"getprop {name}", timeout=20)[1].strip()


def online_devices():
    _, text = adb(None, "devices")
    return [l.split("\t")[0] for l in text.splitlines()[1:] if l.endswith("\tdevice")]


def run_folder(run):
    folder = (ROOT / run).resolve()
    if folder.parent != RUNS.resolve() or not folder.is_dir():
        fail(f"{run!r} isn't a run folder (runs/<name>)")
    return folder


def rel(path):
    return path.relative_to(ROOT).as_posix()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def project_path_for(folder, name):
    if not name:
        text = (folder / "usecase.txt").read_text(encoding="utf-8") if (folder / "usecase.txt").is_file() else ""
        m = re.search(r"^project:\s*(\S+)\s*$", text, re.M)
        name = m.group(1) if m else None
    if not name:
        fail("the run names no project: give --project <name>")
    path = ROOT / "projects" / f"{name}.json"
    if not path.is_file():
        fail(f"no project config projects/{name}.json")
    return path


def device_file(serial, path):
    """What is at a device path now: None if nothing, else sha256, mode, owner and SELinux context."""
    q = shlex.quote(path)
    code, text = shell(serial, f"stat -c '%a %U:%G %C' {q} && sha256sum {q}")
    if code != 0:
        return None
    lines = text.splitlines()
    if len(lines) < 2 or len(lines[0].split()) < 2:
        return None
    parts = lines[0].split()
    return {"sha256": lines[1].split()[0], "mode": parts[0], "owner": parts[1],
            "context": parts[2] if len(parts) > 2 and parts[2] != "?" else None}


def installed_apks(serial, package):
    code, text = shell(serial, f"pm path {shlex.quote(package)}")
    return [l[len("package:"):].strip() for l in text.splitlines() if l.startswith("package:")] if code == 0 else []


def check_lock(serial, folder):
    lock = LOCKS / serial
    if lock.exists():
        held = lock.read_text(encoding="utf-8").splitlines()
        holder = held[0] if held else "?"
        # A run whose result is written has finished, so its lock is only left behind.
        if holder != rel(folder) and not (ROOT / holder / "result.json").is_file():
            fail(f"device {serial} is locked by another run", held_by=held,
                 hint=f"if that run is gone, delete runs/.locks/{serial}")


def take_lock(serial, folder):
    LOCKS.mkdir(parents=True, exist_ok=True)
    (LOCKS / serial).write_text(f"{rel(folder)}\n{now()}\n", encoding="utf-8")


def release_lock(serial, folder):
    lock = LOCKS / serial
    if lock.exists() and lock.read_text(encoding="utf-8").splitlines()[:1] == [rel(folder)]:
        lock.unlink()


# --- plan ---------------------------------------------------------------------------------------

def plan(run, project_name, serial_arg):
    folder = run_folder(run)
    project_path = project_path_for(folder, project_name)
    project = read_json(project_path)
    if not project or not project.get("push"):
        fail(f"{rel(project_path)} has no push section")
    artifacts = read_json(folder / "artifacts.json")
    if not artifacts or not artifacts.get("ok"):
        fail("no successful build in this run: run buildkit first")
    if artifacts.get("project") != project["name"]:
        fail(f"artifacts.json was built for project {artifacts.get('project')}, not {project['name']}: run buildkit again")

    push = project["push"]
    problems = []
    for key in ("install", "restart"):
        if FORBIDDEN.search(push.get(key) or ""):
            problems.append(f"push.{key} is refused by the device-safety rules: {push[key]}")
    for f in artifacts["files"]:
        if not f["device"].startswith("/") or re.search(r"[*?\s;&|`$]", f["device"]) or ".." in f["device"]:
            problems.append(f"device path {f['device']!r}: it must be absolute, with no spaces or shell characters")
        local = ROOT / f["local"]
        if not local.is_file() or sha256(local) != f["sha256"]:
            problems.append(f"{f['local']} changed since the build: run buildkit again")
        if push["mode"] == "data" and not f["device"].startswith("/data/local/tmp/"):
            problems.append(f"data mode pushes only to /data/local/tmp/: {f['device']}")
    if problems:
        fail("the push can't go ahead", problems=problems)

    online = online_devices()
    wanted = serial_arg or project.get("device", {}).get("serial")
    if wanted and wanted not in online:
        fail(f"device {wanted} isn't online", online=online)
    if not wanted and len(online) != 1:
        fail("name the device: " + ("none is connected" if not online else "several are connected"), online=online)
    serial = wanted or online[0]
    check_lock(serial, folder)

    build_type = getprop(serial, "ro.build.type")
    device = {"serial": serial, "fingerprint": getprop(serial, "ro.build.fingerprint"),
              "model": getprop(serial, "ro.product.model"), "android": getprop(serial, "ro.build.version.release"),
              "build_type": build_type, "debuggable": getprop(serial, "ro.debuggable") == "1",
              "boot_completed": getprop(serial, "sys.boot_completed") == "1"}
    if not device["boot_completed"]:
        fail(f"device {serial} hasn't finished booting")
    if push["mode"] == "system" and not device["debuggable"]:
        fail(f"system push needs adb root, and {serial} is a {build_type} build (ro.debuggable=0)",
             hint="use a userdebug or eng build, or an emulator with a Google APIs image started with -writable-system")

    files = []
    for f in artifacts["files"]:
        files.append({"local": f["local"], "device": f["device"], "sha256": f["sha256"], "size": f["size"],
                      "mode": f.get("mode"), "owner": f.get("owner"), "now": device_file(serial, f["device"])})
    package = project.get("app", {}).get("package")
    apks = installed_apks(serial, package) if package else []
    restart = "reboot" if push.get("reboot") else (push.get("restart") or "none")
    data = {"made": now(), "run": rel(folder), "project": project["name"], "project_file": rel(project_path),
            "project_sha256": sha256(project_path), "mode": push["mode"], "device": device, "package": package,
            "installed": apks, "files": files, "install": push.get("install"), "restart": restart,
            "boot_timeout_s": push.get("boot_timeout_s")}
    write_json(folder / "push-plan.json", data)
    (folder / "push-plan.md").write_text(plan_text(folder, data, artifacts), encoding="utf-8")
    out({"plan": rel(folder / "push-plan.md"), "mode": push["mode"], "device": serial,
         "files": [f"{f['local']} -> {f['device']}" for f in files], "restart": restart})


def tests_line(folder):
    result = read_json(folder / "build-result.json")
    if not result or "test" not in result:
        return "not run"
    applied = folder / "backup-src" / "manifest.json"
    if applied.is_file() and applied.stat().st_mtime > (folder / "build-result.json").stat().st_mtime:
        return "not run on this source (the fix was applied after them)"
    test = result["test"]
    return "passed" if test.get("ok") else "**FAILED** (see test.log)"


def plan_text(folder, plan_, artifacts):
    device = plan_["device"]
    lines = [f"# Push plan: {plan_['project']}", ""]
    lines += ["| | |", "|---|---|",
              f"| Device | `{device['serial']}`: {device['model']}, Android {device['android']}, {device['build_type']} build |",
              f"| Mode | {plan_['mode']} |",
              f"| Build | `{artifacts['command']}`: ok in {artifacts['seconds']} s |",
              f"| Unit tests | {tests_line(folder)} |", ""]
    lines += [f"**Warning:** {w}" for w in artifacts.get("warnings", [])]
    if artifacts.get("warnings"):
        lines.append("")
    fix = read_json(folder / "fix.json")
    if fix and (folder / "backup-src" / "manifest.json").is_file():
        lines += [f"Contains the fix: {fix.get('summary', 'see fix.diff')} (`fix.diff`).", ""]
    lines += ["## Files", "", "| File | Device path | sha256 | Now on the device |", "|---|---|---|---|"]
    for f in plan_["files"]:
        now_there = f"a file, {f['now']['sha256'][:12]}…" if f["now"] else "nothing"
        lines.append(f"| `{f['local']}` ({f['size'] // 1024} KB) | `{f['device']}` | {f['sha256'][:12]}… | {now_there} |")
    lines += ["", "## What will happen", ""]
    n = 1
    def step(text):
        nonlocal n
        lines.append(f"{n}. {text}")
        n += 1
    if plan_["mode"] == "system":
        step("`adb root`, then `adb remount`. **The first time, this runs `adb disable-verity` and reboots the device.**")
    step(f"**Backup** into `{rel(folder / BACKUP)}/`: every file above that exists, with its mode, owner and context.")
    if plan_["mode"] == "data" and plan_["package"]:
        step(f"**Backup** of the installed app {plan_['package']}: " +
             (", ".join(f"`{a}`" for a in plan_["installed"]) if plan_["installed"] else "it isn't installed, so a rollback uninstalls it."))
    step("`adb push` each file, set its mode and owner, and compare its sha256 on the device.")
    if plan_["install"]:
        step(f"Install, on the device: `{plan_['install']}`")
    if plan_["restart"] == "reboot":
        step("Restart: **reboot**, then wait for `sys.boot_completed`.")
    elif plan_["restart"] == "none":
        step("No restart.")
    else:
        step(f"Restart, on the device: `{plan_['restart']}`")
    lines += ["", "**If a step or a check fails, the backup is put back by itself.** After a good push, "
              "`rollback` puts it back when you ask.", ""]
    return "\n".join(lines)


# --- push ---------------------------------------------------------------------------------------

class PushFailed(Exception):
    pass


def wait_ready(serial, old_system_server=None):
    """Until apps can run. After `stop; start` sys.boot_completed stays 1, and the package manager
    answers long before activities can start (mBooted), storage is back (/sdcard) and the user is
    unlocked, which is when an ordinary app exists at all."""
    timeout = BOOT_TIMEOUT
    deadline = time.time() + timeout
    up_since = None
    adb(serial, "wait-for-device", timeout=timeout)
    while time.time() < deadline:
        new_server = old_system_server is None or \
            shell(serial, "pidof system_server", timeout=20)[1].strip() not in ("", old_system_server)
        if new_server and getprop(serial, "sys.boot_completed") == "1" and \
                shell(serial, "pm path android", timeout=20)[0] == 0 and \
                "mBooted=true" in shell(serial, "dumpsys activity processes", timeout=30)[1]:
            code, text = shell(serial, "ls /sdcard", timeout=20)
            if code == 0 or "No such file" in text:  # some devices have no /sdcard
                up_since = up_since or time.time()
                # A device with a PIN stays locked until a person unlocks it: it is up, so don't roll back.
                if "RUNNING_UNLOCKED" in shell(serial, "am get-started-user-state 0", timeout=20)[1] or \
                        time.time() - up_since > UNLOCK_TIMEOUT:
                    return True
        time.sleep(2)
    return False


def use_boot_timeout(plan_):
    global BOOT_TIMEOUT
    BOOT_TIMEOUT = plan_.get("boot_timeout_s") or BOOT_TIMEOUT


def get_root(serial):
    code, text = adb(serial, "root")
    if "cannot run as root" in text:
        raise PushFailed(f"adb root: {text}")
    time.sleep(1)
    adb(serial, "wait-for-device", timeout=60)
    for _ in range(15):
        if shell(serial, "id -u", timeout=20)[1].strip() == "0":
            return
        time.sleep(1)
    raise PushFailed("adb root: the device's shell didn't become root")


def reboot(serial, log):
    adb(serial, "reboot")
    log("reboot")
    # Until it has really gone down: boot_completed stays 1 for a moment after the command.
    deadline = time.time() + 60
    while time.time() < deadline and getprop(serial, "sys.boot_completed") == "1":
        time.sleep(1)
    if not wait_ready(serial):
        raise PushFailed(f"the device didn't come back within {BOOT_TIMEOUT} s after the reboot")


def remount(serial, log):
    """adb root and a writable system. The first time it needs disable-verity and a reboot."""
    get_root(serial)
    code, text = adb(serial, "remount")
    log(f"remount: {text.splitlines()[-1] if text else code}")
    if code == 0 and "reboot" not in text.lower():
        return
    code, text = adb(serial, "disable-verity")
    log(f"disable-verity: {text.splitlines()[-1] if text else code}")
    reboot(serial, log)
    get_root(serial)
    code, text = adb(serial, "remount")
    log(f"remount: {text.splitlines()[-1] if text else code}")
    if code != 0 or "reboot" in text.lower():
        raise PushFailed(f"adb remount failed: {text}")


def take_backup(folder, plan_, log):
    serial, backup = plan_["device"]["serial"], folder / BACKUP
    backup.mkdir()
    manifest = {"made": now(), "serial": serial, "mode": plan_["mode"], "project": plan_["project"],
                "package": plan_["package"], "files": [], "apks": [], "pushed": []}
    for f in plan_["files"]:
        current = device_file(serial, f["device"])
        entry = {"device": f["device"], "existed": current is not None}
        if current:
            local = backup / PurePosixPath(f["device"]).relative_to("/")
            local.parent.mkdir(parents=True, exist_ok=True)
            code, text = adb(serial, "pull", f["device"], local, timeout=600)
            if code != 0 or sha256(local) != current["sha256"]:
                raise PushFailed(f"backup of {f['device']} failed: {text}")
            entry.update(current, local=local.relative_to(backup).as_posix())
        manifest["files"].append(entry)
    if plan_["mode"] == "data" and plan_["package"]:
        for i, apk in enumerate(installed_apks(serial, plan_["package"])):
            local = backup / "installed" / f"{i}-{PurePosixPath(apk).name}"
            local.parent.mkdir(parents=True, exist_ok=True)
            code, text = adb(serial, "pull", apk, local, timeout=600)
            if code != 0 or not local.is_file():
                raise PushFailed(f"backup of the installed {apk} failed: {text}")
            manifest["apks"].append({"device": apk, "local": local.relative_to(backup).as_posix(), "sha256": sha256(local)})
    write_json(backup / "manifest.json", manifest)
    log(f"backup: {len([f for f in manifest['files'] if f['existed']])} files, {len(manifest['apks'])} installed APKs")
    return manifest


def set_attributes(serial, path, mode, owner, context):
    q = shlex.quote(path)
    for command in ([f"chmod {shlex.quote(mode)} {q}"] if mode else []) + \
                   ([f"chown {shlex.quote(owner)} {q}"] if owner else []) + \
                   ([f"chcon {shlex.quote(context)} {q}"] if context else []):
        code, text = shell(serial, command)
        if code != 0:
            raise PushFailed(f"{command}: {text}")


def restart_device(serial, plan_, want_reboot, log):
    command = plan_["restart"]
    if want_reboot or command == "reboot":
        reboot(serial, log)
        return "reboot"
    if command == "none":
        return "none"
    framework = re.search(r"(^|[;&\s])stop($|[;&\s])", command)
    old = shell(serial, "pidof system_server", timeout=20)[1].strip() if framework else None
    code, text = shell(serial, command)
    log(f"restart: {command}")
    if code != 0:
        raise PushFailed(f"restart {command}: {text}")
    if not wait_ready(serial, old):
        raise PushFailed(f"the device didn't come back within {BOOT_TIMEOUT} s after: {command}")
    return command


def do_push(folder, plan_, want_reboot, log, result):
    serial = plan_["device"]["serial"]
    backup = folder / BACKUP
    if plan_["mode"] == "system":
        remount(serial, log)
    # A second push from this run keeps the first backup: rollback goes back to the original.
    manifest = read_json(backup / "manifest.json") if (backup / "manifest.json").is_file() else None
    if manifest is None:
        if backup.exists():
            shutil.rmtree(backup)
        manifest = take_backup(folder, plan_, log)
    result["backup"] = rel(backup)

    if {f["device"] for f in plan_["files"]} - {f["device"] for f in manifest["files"]}:
        raise PushFailed("this plan has files the run's first push didn't have: roll back first")
    for f in plan_["files"]:
        if plan_["mode"] == "system":
            shell(serial, f"mkdir -p {shlex.quote(str(PurePosixPath(f['device']).parent))}")
        code, text = adb(serial, "push", ROOT / f["local"], f["device"], timeout=600)
        if code != 0:
            raise PushFailed(f"adb push {f['local']}: {text}")
        log(f"pushed {f['device']}")
        manifest["pushed"] = sorted(set(manifest["pushed"]) | {f["device"]})
        write_json(backup / "manifest.json", manifest)
        before = next(b for b in manifest["files"] if b["device"] == f["device"])
        if plan_["mode"] == "system":
            set_attributes(serial, f["device"], f.get("mode") or before.get("mode"),
                           f.get("owner") or before.get("owner"), before.get("context"))
        elif f.get("mode"):
            set_attributes(serial, f["device"], f["mode"], None, None)
        if not before["existed"] and plan_["mode"] == "system":
            shell(serial, f"restorecon -R {shlex.quote(str(PurePosixPath(f['device']).parent))}")
        there = device_file(serial, f["device"])
        ok = bool(there) and there["sha256"] == f["sha256"]
        result["checks"].append({"check": f"sha256 of {f['device']}", "ok": ok,
                                 "device": there["sha256"] if there else None, "built": f["sha256"]})
        if not ok:
            raise PushFailed(f"the checksum of {f['device']} on the device isn't the built file's")

    if plan_["install"]:
        code, text = shell(serial, plan_["install"], timeout=300)
        log(f"install: {text.splitlines()[0] if text else code}")
        if code != 0 or "Failure" in text or "failed" in text.lower():
            raise PushFailed("install: " + "\n".join(text.splitlines()[:5]))

    result["restart"] = restart_device(serial, plan_, want_reboot, log)
    result["checks"].append({"check": "sys.boot_completed", "ok": getprop(serial, "sys.boot_completed") == "1"})
    if not result["checks"][-1]["ok"]:
        raise PushFailed("the device isn't booted after the restart")

    package, apks = plan_["package"], [f for f in plan_["files"] if f["device"].endswith(".apk")]
    if package and apks:
        paths = installed_apks(serial, package)
        result["installed"] = paths
        wanted = {f["sha256"] for f in apks}
        on_device = {(device_file(serial, p) or {}).get("sha256") for p in paths}
        ok = bool(wanted & on_device)
        result["checks"].append({"check": f"the package manager has the built APK of {package}", "ok": ok, "paths": paths})
        if not ok:
            raise PushFailed(f"{package} isn't running from the pushed APK: pm path gives {paths}")


def push(run, want_reboot):
    folder = run_folder(run)
    plan_ = read_json(folder / "push-plan.json")
    if not plan_:
        fail("no push-plan.json: run plan and ask Gate 2 first")
    serial = plan_["device"]["serial"]
    project_file = ROOT / plan_["project_file"]
    problems = []
    if not (read_json(folder / "artifacts.json") or {}).get("ok"):
        problems.append("the latest build in this run failed")
    if not project_file.is_file() or sha256(project_file) != plan_["project_sha256"]:
        problems.append(f"{plan_['project_file']} changed since the plan")
    for f in plan_["files"]:
        local = ROOT / f["local"]
        if not local.is_file() or sha256(local) != f["sha256"]:
            problems.append(f"{f['local']} isn't the file in the plan")
    if serial not in online_devices():
        problems.append(f"device {serial} isn't online")
    elif getprop(serial, "ro.build.fingerprint") != plan_["device"]["fingerprint"]:
        problems.append(f"device {serial} isn't the device in the plan")
    if problems:
        fail("this isn't what Gate 2 showed: run plan and ask Gate 2 again", problems=problems)
    check_lock(serial, folder)
    # The files are as in the plan; the config's mode and owner come along for the push.
    project = read_json(project_file)
    by_device = {f["device"]: f for f in project["push"]["files"]}
    for f in plan_["files"]:
        f.update({k: by_device.get(f["device"], {}).get(k) for k in ("mode", "owner")})

    use_boot_timeout(plan_)
    take_lock(serial, folder)
    steps, result = [], {"run": rel(folder), "device": serial, "mode": plan_["mode"], "started": now(),
                         "checks": [], "rolled_back": False}
    def log(text):
        steps.append(text)
    result["steps"] = steps
    try:
        do_push(folder, plan_, want_reboot, log, result)
        result["ok"] = True
        code = 0
    except PushFailed as e:
        result["ok"], result["error"] = False, str(e)
        code = 1
        if (folder / BACKUP / "manifest.json").is_file():
            result["rollback"] = do_rollback(folder, log)
            result["rolled_back"] = result["rollback"]["ok"]
            if result["rolled_back"]:
                shutil.rmtree(folder / BACKUP)
    result["finished"] = now()
    write_json(folder / "push-result.json", result)
    release_lock(serial, folder)
    out(result, code)


# --- status and rollback ------------------------------------------------------------------------

def status(run):
    folder = run_folder(run)
    manifest = read_json(folder / BACKUP / "manifest.json")
    if manifest is None:
        fail("no backup in this run: nothing was pushed, or it was already rolled back")
    plan_ = read_json(folder / "push-plan.json") or {}
    serial = manifest["serial"]
    built = {f["device"]: f["sha256"] for f in plan_.get("files", [])}
    files = []
    for f in manifest["files"]:
        current = device_file(serial, f["device"])
        now_sha = current["sha256"] if current else None
        files.append({"device": f["device"], "now": now_sha, "backup": f.get("sha256"), "pushed": built.get(f["device"]),
                      "state": "as pushed" if now_sha == built.get(f["device"]) else
                               "as before the push" if now_sha == f.get("sha256") else "changed since the push",
                      "rollback_will": "restore the backup" if f["existed"] else "delete it"})
    out({"device": serial, "online": serial in online_devices(), "mode": manifest["mode"], "files": files,
         "apks": [a["device"] for a in manifest["apks"]],
         "rollback_also": "reinstalls the backed-up app" if manifest["apks"] else
                          (f"uninstalls {manifest['package']}" if manifest["mode"] == "data" and manifest["package"] else None)})


def do_rollback(folder, log):
    """Puts the backup back and checks it. Never raises: it says what it could and couldn't do."""
    backup = folder / BACKUP
    manifest = read_json(backup / "manifest.json")
    plan_ = read_json(folder / "push-plan.json") or {}
    use_boot_timeout(plan_)
    serial, errors, checks = manifest["serial"], [], []
    try:
        if manifest["mode"] == "system":
            remount(serial, log)
        for f in manifest["files"]:
            q = shlex.quote(f["device"])
            if f["existed"]:
                code, text = adb(serial, "push", backup / f["local"], f["device"], timeout=600)
                if code != 0:
                    errors.append(f"push {f['device']}: {text}")
                    continue
                if manifest["mode"] == "system":
                    set_attributes(serial, f["device"], f.get("mode"), f.get("owner"), f.get("context"))
                else:
                    set_attributes(serial, f["device"], f.get("mode"), None, None)
            elif f["device"] in manifest["pushed"]:
                code, text = shell(serial, f"rm -f {q}")
                if code != 0:
                    errors.append(f"rm {f['device']}: {text}")
                    continue
                if manifest["mode"] == "system":
                    # The folder the push made for this file, if nothing else is in it.
                    shell(serial, f"rmdir {shlex.quote(str(PurePosixPath(f['device']).parent))}")
            there = device_file(serial, f["device"])
            ok = (there or {}).get("sha256") == f.get("sha256")
            checks.append({"check": f"{f['device']} is as before", "ok": ok})
            log(f"restored {f['device']}" if f["existed"] else f"removed {f['device']}")
        package = manifest.get("package")
        if manifest["mode"] == "data" and package:
            locals_ = [backup / a["local"] for a in manifest["apks"]]
            if locals_:
                args = ("install", "-r", "-d", "-t", locals_[0]) if len(locals_) == 1 else \
                       ("install-multiple", "-r", "-d", "-t", *locals_)
                code, text = adb(serial, *args, timeout=600)
                log(f"reinstalled {package}: {text.splitlines()[-1] if text else code}")
                if code != 0 or "Success" not in text:
                    errors.append(f"reinstalling {package}: {text}")
                on_device = {(device_file(serial, p) or {}).get("sha256") for p in installed_apks(serial, package)}
                ok = {a["sha256"] for a in manifest["apks"]} <= on_device
                checks.append({"check": f"{package} is the backed-up APK", "ok": ok})
            elif installed_apks(serial, package):
                code, text = adb(serial, "uninstall", package)
                log(f"uninstalled {package}: {text}")
                checks.append({"check": f"{package} isn't installed, as before", "ok": not installed_apks(serial, package)})
        command = plan_.get("restart", "none")
        if manifest["mode"] == "system" or command == "reboot":
            restart_device(serial, {"restart": command}, False, log)
        elif command != "none":
            shell(serial, command)
        checks.append({"check": "sys.boot_completed", "ok": getprop(serial, "sys.boot_completed") == "1"})
    except PushFailed as e:
        errors.append(str(e))
    ok = not errors and all(c["ok"] for c in checks)
    return {"ok": ok, "errors": errors, "checks": checks}


def rollback(run, force):
    folder = run_folder(run)
    manifest = read_json(folder / BACKUP / "manifest.json")
    if manifest is None:
        fail("no backup in this run: nothing was pushed, or it was already rolled back")
    plan_ = read_json(folder / "push-plan.json") or {}
    serial = manifest["serial"]
    if serial not in online_devices():
        fail(f"device {serial} isn't online")
    check_lock(serial, folder)
    built = {f["device"]: f["sha256"] for f in plan_.get("files", [])}
    changed = []
    for f in manifest["files"]:
        current = (device_file(serial, f["device"]) or {}).get("sha256")
        if current not in (built.get(f["device"]), f.get("sha256")):
            changed.append(f["device"])
    if changed and not force:
        fail("these files changed on the device since the push, so a rollback would overwrite that",
             changed=changed, hint="ask the user, then use --force")
    take_lock(serial, folder)
    steps = []
    result = do_rollback(folder, steps.append)
    result["steps"] = steps
    done = read_json(folder / "push-result.json") or {}
    done.update(rollback=result, rolled_back=result["ok"])
    write_json(folder / "push-result.json", done)
    release_lock(serial, folder)
    if result["ok"]:
        shutil.rmtree(folder / BACKUP)  # all restored and checked, like fixkit's undo
    out(result, 0 if result["ok"] else 1)


def main(argv):
    options = {}
    for name in ("--project", "--serial"):
        if name in argv:
            i = argv.index(name)
            options[name] = argv[i + 1] if i + 1 < len(argv) else None
            argv = argv[:i] + argv[i + 2:]
    flags = {a for a in argv if a in ("--reboot", "--force")}
    argv = [a for a in argv if a not in flags]
    if len(argv) == 2:
        if argv[0] == "plan":
            return plan(argv[1], options.get("--project"), options.get("--serial"))
        if argv[0] == "push":
            return push(argv[1], "--reboot" in flags)
        if argv[0] == "status":
            return status(argv[1])
        if argv[0] == "rollback":
            return rollback(argv[1], "--force" in flags)
    fail("usage: pushkit.py plan <run> [--project NAME] [--serial S] | push <run> [--reboot] | status <run> | rollback <run> [--force]")


if __name__ == "__main__":
    main(sys.argv[1:])
