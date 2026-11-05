"""Scores the agents against the answer key in eval/answers/.

    python eval/score.py [--answers eval/answers/testbench.json]

For each planted bug it takes the newest run of its use case that has a triage.json and scores:
- triage (S4): the class, and whether it says the code is ours; a bug report;
- the investigation (S5): the root cause's file, and its line within LINE_SLACK of the key's (or
  of one of the key's "also" lines); whether the fix built and its unit tests passed
  (build-result.json).
Later stages add the push and the verification. The result is printed and saved in eval/results/
(git-ignored).
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
LINE_SLACK = 3


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def newest_triaged(usecase):
    stem = Path(usecase).stem
    for folder in sorted(RUNS.glob(f"*-{stem}"), reverse=True):
        if (folder / "triage.json").is_file():
            return folder
    return None


def investigation(folder, bug):
    found = {"root_cause": None, "line_ok": None, "builds": None}
    inv = read_json(folder / "investigation.json")
    if inv is None:
        return found
    cause = inv.get("root_cause") or {}
    found["root_cause"] = f"{cause.get('file')}:{cause.get('line')}"
    places = [(bug["file"], bug["line"])] + [(a["file"], a["line"]) for a in bug.get("also", [])]
    found["line_ok"] = any(cause.get("file") == f and isinstance(cause.get("line"), int)
                           and abs(cause["line"] - line) <= LINE_SLACK for f, line in places)
    built = read_json(folder / "build-result.json")
    if built is not None:
        found["builds"] = bool(built.get("ok"))
    return found


def score(answers):
    rows = []
    for bug in answers["bugs"]:
        folder = newest_triaged(bug["usecase"])
        row = {"bug": bug["id"], "usecase": bug["usecase"], "want_class": bug["class"], "run": None,
               "class": None, "ours": None, "class_ok": False, "ours_ok": False, "report": False,
               "root_cause": None, "line_ok": None, "builds": None}
        if folder:
            triage = read_json(folder / "triage.json") or {}
            row.update(run=folder.relative_to(ROOT).as_posix(), **{k: triage.get(k) for k in ("class", "ours")})
            row["repro"] = triage.get("repro")
            row["class_ok"] = triage.get("class") == bug["class"]
            row["ours_ok"] = triage.get("ours") is True  # every planted bug is in the app's code
            row["report"] = (folder / "bug-report.md").is_file()
            row.update(investigation(folder, bug))
        rows.append(row)
    return rows


def mark(value):
    return "-" if value is None else "OK" if value else "X"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", default=str(ROOT / "eval" / "answers" / "testbench.json"))
    args = parser.parse_args()
    answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
    rows = score(answers)

    print(f"{'bug':4} {'want':13} {'got':13} {'class':5} {'ours':5} {'report':6} {'line':5} {'build':5} run")
    for r in rows:
        print(f"{r['bug']:4} {r['want_class']:13} {str(r['class']):13} {mark(r['class_ok']):5} "
              f"{mark(r['ours_ok']):5} {'yes' if r['report'] else 'no':6} {mark(r['line_ok']):5} "
              f"{mark(r['builds']):5} {r['run'] or '(no triaged run)'}")
    total = len(rows)
    counts = {
        "class": sum(r["class_ok"] for r in rows),
        "ours": sum(r["ours_ok"] for r in rows),
        "reports": sum(r["report"] for r in rows),
        "root_cause": sum(bool(r["line_ok"]) for r in rows),
        "builds": sum(bool(r["builds"]) for r in rows),
    }
    print(", ".join(f"{k.replace('_', ' ')} {v}/{total}" for k, v in counts.items()))

    results = ROOT / "eval" / "results"
    results.mkdir(parents=True, exist_ok=True)
    out = results / f"{datetime.now():%Y%m%d-%H%M%S}-{answers['project']}.json"
    summary = {k: f"{v}/{total}" for k, v in counts.items()}
    out.write_text(json.dumps({"project": answers["project"], "scored": datetime.now().isoformat(), **summary,
                               "rows": rows}, indent=2) + "\n", encoding="utf-8")
    print(f"saved {out.relative_to(ROOT).as_posix()}")
    sys.exit(0 if all(v == total for v in counts.values()) else 1)


if __name__ == "__main__":
    main()
