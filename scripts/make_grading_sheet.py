"""Two graders, independently: "would I send this receipt to the merchant without editing?" (Assignment 4).

1. Make the sheet from the raw outputs of an endpoint run (saved by run_eval_set.py):
       uv run python -m scripts.make_grading_sheet --run evals/runs/<date>_endpoint.jsonl
   -> evals/grading_v0.csv. Each grader fills their own column with yes / no, without looking at
      the other column (grader_a_send, grader_b_send).
2. Score it:
       uv run python -m scripts.make_grading_sheet --score
   -> receipts both graders would send, agreement, Cohen's kappa: the numbers for report_v0.md §3.
"""
import argparse
import csv
import glob
import json

COLS = ["id", "segment", "expected", "route", "decision", "clause", "amount_eur", "receipt",
        "grader_a_send", "grader_b_send", "notes"]


def make(run_path: str, eval_path: str, out: str) -> None:
    rows = {r["id"]: r for r in csv.DictReader(open(eval_path, encoding="utf-8"))}
    sheet = []
    for line in open(run_path, encoding="utf-8"):
        x = json.loads(line)
        try:
            d = json.loads(x["raw"]) if x.get("raw") else {}
        except (json.JSONDecodeError, TypeError):
            d = {}
        r = rows.get(x["id"], {})
        sheet.append({"id": x["id"], "segment": r.get("segment", ""), "expected": r.get("expected_output_or_action", ""),
                      "route": x["route"], "decision": d.get("decision", "(no valid output)"), "clause": d.get("clause", ""),
                      "amount_eur": d.get("amount_eur", ""), "receipt": d.get("receipt", x.get("raw") or ""),
                      "grader_a_send": "", "grader_b_send": "", "notes": ""})
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(sheet)
    print(f"{len(sheet)} receipts -> {out}. Graders: fill grader_a_send / grader_b_send with yes or no, separately.")


def score(path: str) -> None:
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8"))
            if r["grader_a_send"].strip().lower() in ("yes", "no") and r["grader_b_send"].strip().lower() in ("yes", "no")]
    n = len(rows)
    if not n:
        print("No row graded by both graders yet.")
        return
    a = [r["grader_a_send"].strip().lower() == "yes" for r in rows]
    b = [r["grader_b_send"].strip().lower() == "yes" for r in rows]
    both = sum(x and y for x, y in zip(a, b, strict=False))
    agree = sum(x == y for x, y in zip(a, b, strict=False))
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    kappa = (agree / n - pe) / (1 - pe) if pe < 1 else 1.0
    print(f"graded by both            {n}")
    print(f"both would send unedited  {both} ({100 * both / n:.0f}%)")
    print(f"graders agree             {agree}/{n} · Cohen's kappa {kappa:.2f}")
    print("disagreements:", [r["id"] for r, x, y in zip(rows, a, b, strict=False) if x != y])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="evals/runs/<date>_endpoint.jsonl (default: the latest endpoint run)")
    ap.add_argument("--eval", default="evals/eval_set_v0.csv")
    ap.add_argument("--out", default="evals/grading_v0.csv")
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.score:
        score(a.out)
    else:
        runs = sorted(glob.glob("evals/runs/*_endpoint.jsonl"))
        run = a.run or (runs[-1] if runs else None)
        if not run:
            raise SystemExit("No endpoint run saved yet: run `run_eval_set --endpoint` first.")
        make(run, a.eval, a.out)
