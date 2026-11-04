"""Writes eval/answers/testbench.json: where each planted bug in the test bench is.

    python eval/make_answers.py

The line of each bug is found from its code, so the key stays right when a file changes around it.
The key lives outside every source root: the agents mustn't read it.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = "testbench/app/src/main"

BUGS = [
    {
        "id": "B1", "usecase": "usecases/testbench/01-pairing-bt-off.txt",
        "class": "crash", "signature": "java.lang.NullPointerException at PairingActivity.onResume",
        "file": f"{SRC}/java/dev/liveview/testbench/PairingActivity.kt",
        "code": "scanner!!.start",
        "cause": "NearbyScanner.create() returns null when Bluetooth is off; onResume uses it with !!.",
        "fix": "Handle the null scanner: say Bluetooth is off (and disable Scan) instead of starting it.",
    },
    {
        "id": "B2", "usecase": "usecases/testbench/02-scan.txt",
        "class": "anr", "signature": "ANR in dev.liveview.testbench (Input dispatching timed out)",
        "file": f"{SRC}/java/dev/liveview/testbench/data/NearbyScanner.kt",
        "code": "return fullScan.poll(timeoutSeconds, TimeUnit.SECONDS)",
        "also": [{"file": f"{SRC}/java/dev/liveview/testbench/PairingActivity.kt", "code": "scanner?.scanNow("}],
        "cause": "scanNow() blocks up to 12 s waiting for the full scan, and PairingActivity calls it on the main thread.",
        "fix": "Run the full scan off the main thread (a callback or a thread in scan()) and post the result.",
    },
    {
        "id": "B3", "usecase": "usecases/testbench/03-pairing-title.txt",
        "class": "wrong-screen", "signature": "the title reads \"Pair new devcie\"",
        "file": f"{SRC}/res/values/strings.xml",
        "code": "<string name=\"pairing_title\">",
        "cause": "A typo in the string resource.",
        "fix": "pairing_title = \"Pair new device\".",
    },
    {
        "id": "B4", "usecase": "usecases/testbench/04-settings.txt",
        "class": "error-dialog", "signature": "E/Settings: Couldn't load the settings, java.lang.NumberFormatException: For input string: \"12s\"",
        "file": f"{SRC}/java/dev/liveview/testbench/data/SettingsStore.kt",
        "code": "fun parseSeconds(value: String): Int = value.trim().toInt()",
        "cause": "Durations are stored as \"12s\" (the default and save()), but parseSeconds() expects a plain number.",
        "fix": "parseSeconds() drops the trailing \"s\" (value.trim().removeSuffix(\"s\").toInt()); a unit test for \"12s\".",
    },
    {
        "id": "B5", "usecase": "usecases/testbench/05-devices-log.txt",
        "class": "log-only", "signature": "E/DeviceRepository: Couldn't open the icon for …, java.io.FileNotFoundException: …/filesicons/….png",
        "file": f"{SRC}/java/dev/liveview/testbench/data/DeviceRepository.kt",
        "code": "File(context.filesDir.path + \"icons\")",
        "cause": "The icon folder's path is built without a separator (files + icons = filesicons); IconCache writes them to files/icons.",
        "fix": "File(context.filesDir, \"icons\").",
    },
    {
        "id": "B6", "usecase": "usecases/testbench/06-devices-fast.txt",
        "class": "slow", "signature": "I/Devices: Showing 24 devices after about 5000 ms (the use case allows 2 s)",
        "file": f"{SRC}/java/dev/liveview/testbench/data/DeviceRepository.kt",
        "code": "all().sortedWith { a, b -> signalStrength(b).compareTo(signalStrength(a)) }",
        "cause": "The comparator measures both devices' signal (30 ms each) on every comparison: about 100 comparisons.",
        "fix": "Measure each device once, then sort: all().map { it to signalStrength(it) }.sortedByDescending { it.second }.map { it.first }.",
    },
    {
        "id": "B7", "usecase": "usecases/testbench/07-device-battery.txt",
        "class": "flaky", "signature": "about half the runs show \"Battery: —\"",
        "file": f"{SRC}/java/dev/liveview/testbench/DeviceDetailsActivity.kt",
        "code": "val current = details",
        "cause": "The name thread copies `details` before its wait and writes the copy back after it, losing a battery level written meanwhile.",
        "fix": "Read and update `details` together after the wait, under a lock or on the main thread (runOnUiThread { details = details.copy(...) }).",
    },
]


def line_of(file: str, code: str) -> int:
    lines = (ROOT / file).read_text(encoding="utf-8").splitlines()
    hits = [i + 1 for i, line in enumerate(lines) if code in line]
    if len(hits) != 1:
        raise SystemExit(f"{file}: {code!r} found {len(hits)} times (want once)")
    return hits[0]


def main() -> None:
    out = []
    for bug in BUGS:
        entry = {k: v for k, v in bug.items() if k not in ("code", "also")}
        entry["line"] = line_of(bug["file"], bug["code"])
        if "also" in bug:
            entry["also"] = [{"file": a["file"], "line": line_of(a["file"], a["code"])} for a in bug["also"]]
        out.append(entry)
    path = ROOT / "eval" / "answers" / "testbench.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"project": "lv-testbench", "owner": "dev.liveview.testbench", "bugs": out},
                               indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for e in out:
        print(f"{e['id']} {e['class']:12} {e['file'].rsplit('/', 1)[1]}:{e['line']}")


if __name__ == "__main__":
    main()
