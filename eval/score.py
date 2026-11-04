"""Scores the agents against the answer key in eval/answers/.

    python eval/score.py [--answers eval/answers/testbench.json]

Stage S4 scores triage: for each planted bug, the newest run of its use case that has a
triage.json, its class, and whether it says the code is ours. Later stages add the file:line, the
fix and the verification. The result is printed and saved in eval/results/ (git-ignored).
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"


def newest_triaged(usecase):
    stem = Path(usecase).stem
    for folder in sorted(RUNS.glob(f"*-{stem}"), reverse=True):
        if (folder / "triage.json").is_file():
            return folder
    return None


def score(answers):
    rows = []
    for bug in answers["bugs"]:
        folder = newest_triaged(bug["usecase"])
        row = {"bug": bug["id"], "usecase": bug["usecase"], "want_class": bug["class"], "run": None,
               "class": None, "ours": None, "class_ok": False, "ours_ok": False, "report": False}
        if folder:
            triage = json.loads((folder / "triage.json").read_text(encoding="utf-8"))
            row.update(run=folder.relative_to(ROOT).as_posix(), **{k: triage.get(k) for k in ("class", "ours")})
            row["repro"] = triage.get("repro")
            row["class_ok"] = triage.get("class") == bug["class"]
            row["ours_ok"] = triage.get("ours") is True  # every planted bug is in the app's code
            row["report"] = (folder / "bug-report.md").is_file()
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", default=str(ROOT / "eval" / "answers" / "testbench.json"))
    args = parser.parse_args()
    answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
    rows = score(answers)

    print(f"{'bug':4} {'want':13} {'got':13} {'class':5} {'ours':5} {'report':6} run")
    for r in rows:
        print(f"{r['bug']:4} {r['want_class']:13} {str(r['class']):13} {'OK' if r['class_ok'] else 'X':5} "
              f"{'OK' if r['ours_ok'] else 'X':5} {'yes' if r['report'] else 'no':6} {r['run'] or '(no triaged run)'}")
    total = len(rows)
    classes = sum(r["class_ok"] for r in rows)
    ours = sum(r["ours_ok"] for r in rows)
    reports = sum(r["report"] for r in rows)
    print(f"class {classes}/{total}, ours {ours}/{total}, reports {reports}/{total}")

    results = ROOT / "eval" / "results"
    results.mkdir(parents=True, exist_ok=True)
    out = results / f"{datetime.now():%Y%m%d-%H%M%S}-{answers['project']}-triage.json"
    out.write_text(json.dumps({"project": answers["project"], "stage": "S4", "scored": datetime.now().isoformat(),
                               "class": f"{classes}/{total}", "ours": f"{ours}/{total}",
                               "reports": f"{reports}/{total}", "rows": rows}, indent=2) + "\n", encoding="utf-8")
    print(f"saved {out.relative_to(ROOT).as_posix()}")
    sys.exit(0 if classes == total and ours == total else 1)


if __name__ == "__main__":
    main()
