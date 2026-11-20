"""Assignment 5 §5: make the judge trustworthy — golden sheet, LLM judge, two agreement rates.

    # 1. after an endpoint run on the eval-set (run_eval_set --endpoint saves evals/runs/<stamp>_endpoint.jsonl):
    uv run python -m scripts.judge_kit sheet --eval evals/eval_set_v1.csv          # -> evals/grading_v1.csv (30 golden rows)
    # 2. two people fill grader_a_verdict / grader_b_verdict (sendable | needs_edit | escalate), separately
    # 3. the judge grades the same 30 rows (Gemini, temperature 0, prompt = evals/judge_prompt.txt):
    uv run python -m scripts.judge_kit judge
    # 4. the two numbers for evals/README.md and 05_metrics.md §5:
    uv run python -m scripts.judge_kit score

The 30 golden rows are stratified by language and expected clause (seed 42) and never change afterwards
(their ids are written to evals/golden_30.txt). Labels stay human: the judge only grades the agent's receipt.
Known bias to report: the judge (Gemini) is the same model family as the photo describer, not as the drafter (Phi-3).
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

VERDICTS = ["sendable", "needs_edit", "escalate"]
SHEET_COLS = ["id", "segment", "input", "expected", "route", "decision", "clause", "amount_eur", "receipt",
              "grader_a_verdict", "grader_b_verdict", "judge_verdict", "judge_answers", "judge_evidence", "notes"]
GOLDEN_FILE = "evals/golden_30.txt"


def _clause(expected: str) -> str:
    for part in expected.replace("·", " ").split():
        if part.startswith("R") and part[1:].isdigit():
            return part
    return "other"


def pick_golden(rows: list[dict[str, str]], n: int = 30, seed: int = 42) -> list[str]:
    """Stratified by (language, expected clause): round-robin over the strata so every one is represented."""
    strata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in rows:
        lang = (r.get("segment") or "").split("·")[0].strip() or "?"
        strata[(lang, _clause(r.get("expected_output_or_action", "")))].append(r["id"])
    rng = random.Random(seed)
    for ids in strata.values():
        rng.shuffle(ids)
    chosen: list[str] = []
    keys = sorted(strata)
    while len(chosen) < min(n, len(rows)):
        for k in keys:
            if strata[k] and len(chosen) < n:
                chosen.append(strata[k].pop())
    return sorted(chosen)


def make_sheet(run_path: str, eval_path: str, out: str, n: int) -> list[str]:
    rows = {r["id"]: r for r in csv.DictReader(open(eval_path, encoding="utf-8"))}
    outputs = {}
    for line in open(run_path, encoding="utf-8"):
        x = json.loads(line)
        outputs[x["id"]] = x
    golden_path = Path(GOLDEN_FILE)
    if golden_path.exists():
        golden = golden_path.read_text(encoding="utf-8").split()
    else:
        golden = pick_golden([r for i, r in rows.items() if i in outputs], n)
        golden_path.write_text("\n".join(golden) + "\n", encoding="utf-8")
    sheet = []
    for gid in golden:
        x, r = outputs.get(gid, {}), rows.get(gid, {})
        try:
            d = json.loads(x["raw"]) if x.get("raw") else {}
        except (json.JSONDecodeError, TypeError):
            d = {}
        sheet.append({"id": gid, "segment": r.get("segment", ""), "input": r.get("input_the_agent_receives", ""),
                      "expected": r.get("expected_output_or_action", ""), "route": x.get("route", ""),
                      "decision": d.get("decision", "(no valid output)"), "clause": d.get("clause", ""),
                      "amount_eur": d.get("amount_eur", ""), "receipt": d.get("receipt", x.get("raw") or ""),
                      "grader_a_verdict": "", "grader_b_verdict": "", "judge_verdict": "", "judge_answers": "",
                      "judge_evidence": "", "notes": ""})
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLS)
        w.writeheader()
        w.writerows(sheet)
    return golden


def judge_prompt(row: dict[str, str], template: str) -> str:
    return (template.replace("{claim}", row["input"]).replace("{expected}", row["expected"])
            .replace("{decision}", str(row["decision"])).replace("{clause}", str(row["clause"]))
            .replace("{amount_eur}", str(row["amount_eur"])).replace("{receipt}", str(row["receipt"])))


def run_judge(sheet: str, model_name: str, location: str) -> None:
    import vertexai
    from dotenv import load_dotenv
    from vertexai.generative_models import GenerationConfig, GenerativeModel

    load_dotenv()
    vertexai.init(project=os.getenv("GCP_PROJECT_ID") or os.environ["GOOGLE_CLOUD_PROJECT"], location=location)
    model = GenerativeModel(model_name)
    schema = {"type": "OBJECT", "properties": {
        "evidence": {"type": "ARRAY", "items": {"type": "STRING"}},
        "answers": {"type": "ARRAY", "items": {"type": "STRING", "enum": ["YES", "NO"]}},
        "verdict": {"type": "STRING", "enum": VERDICTS}},
        "required": ["evidence", "answers", "verdict"], "propertyOrdering": ["evidence", "answers", "verdict"]}
    config = GenerationConfig(temperature=0, response_mime_type="application/json", response_schema=schema)
    template = Path("evals/judge_prompt.txt").read_text(encoding="utf-8")
    rows = list(csv.DictReader(open(sheet, encoding="utf-8")))
    for r in rows:
        for wait in (5, 20, 60, None):
            try:
                out = json.loads(model.generate_content(judge_prompt(r, template), generation_config=config).text)
                r["judge_verdict"], r["judge_answers"] = out["verdict"], " ".join(out["answers"])
                r["judge_evidence"] = " | ".join(out["evidence"])
                break
            except Exception as error:  # noqa: BLE001  (429 quota: wait and retry)
                if wait is None or "429" not in str(error):
                    r["judge_verdict"], r["judge_evidence"] = "error", str(error)[:120]
                    break
                time.sleep(wait)
        time.sleep(1)
    with open(sheet, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"judge ({model_name}, {location}) graded {len(rows)} rows -> {sheet}")


def agreement(a: list[str], b: list[str]) -> tuple[float, float]:
    """Share of rows where a == b, and Cohen's kappa over the three verdicts."""
    n = len(a)
    if not n:
        return 0.0, 0.0
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pe = sum((a.count(v) / n) * (b.count(v) / n) for v in VERDICTS)
    return po, ((po - pe) / (1 - pe) if pe < 1 else 1.0)


def score(sheet: str) -> dict[str, Any]:
    rows = list(csv.DictReader(open(sheet, encoding="utf-8")))
    norm = [{"id": (r.get("id") or "").strip(),
             **{k: (r.get(k) or "").strip().lower() for k in ("grader_a_verdict", "grader_b_verdict", "judge_verdict")}}
            for r in rows]
    hh = [r for r in norm if r["grader_a_verdict"] in VERDICTS and r["grader_b_verdict"] in VERDICTS]
    hh_po, hh_k = agreement([r["grader_a_verdict"] for r in hh], [r["grader_b_verdict"] for r in hh])
    # human-judge: against the rows where the two humans agree (the consensus label)
    cons = [r for r in hh if r["grader_a_verdict"] == r["grader_b_verdict"] and r["judge_verdict"] in VERDICTS]
    hj_po, hj_k = agreement([r["grader_a_verdict"] for r in cons], [r["judge_verdict"] for r in cons])
    sendable = sum(r["grader_a_verdict"] == r["grader_b_verdict"] == "sendable" for r in hh)
    result = {
        "rows_graded_by_both": len(hh), "human_human_agreement": hh_po, "human_human_kappa": hh_k,
        "rows_with_consensus_and_judge": len(cons), "human_judge_agreement": hj_po, "human_judge_kappa": hj_k,
        "both_humans_sendable": sendable,
        "human_disagreements": [r["id"] for r in hh if r["grader_a_verdict"] != r["grader_b_verdict"]],
        "judge_disagreements": [f"{r['id']} (humans {r['grader_a_verdict']}, judge {r['judge_verdict']})"
                                for r in cons if r["judge_verdict"] != r["grader_a_verdict"]],
    }
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("--run", help="evals/runs/<stamp>_endpoint.jsonl (default: the latest)")
    s.add_argument("--eval", default="evals/eval_set_v1.csv")
    s.add_argument("--out", default="evals/grading_v1.csv")
    s.add_argument("--n", type=int, default=30)
    j = sub.add_parser("judge")
    j.add_argument("--sheet", default="evals/grading_v1.csv")
    j.add_argument("--model", default=os.getenv("JUDGE_MODEL", "gemini-3.8-flash"))
    j.add_argument("--location", default=os.getenv("JUDGE_LOCATION", "eu"))
    c = sub.add_parser("score")
    c.add_argument("--sheet", default="evals/grading_v1.csv")
    a = ap.parse_args()
    if a.cmd == "sheet":
        runs = sorted(glob.glob("evals/runs/*_endpoint.jsonl"))
        run = a.run or (runs[-1] if runs else None)
        if not run:
            raise SystemExit("No endpoint run saved yet: run `scripts.run_eval_set --endpoint` on the eval-set first.")
        golden = make_sheet(run, a.eval, a.out, a.n)
        print(f"{len(golden)} golden rows -> {a.out} (ids in {GOLDEN_FILE}). Two graders fill their verdict column, separately.")
    elif a.cmd == "judge":
        run_judge(a.sheet, a.model, a.location)
    else:
        r = score(a.sheet)
        print(f"human-human: {r['human_human_agreement']:.0%} on {r['rows_graded_by_both']} rows (kappa {r['human_human_kappa']:.2f})")
        print(f"human-judge: {r['human_judge_agreement']:.0%} on {r['rows_with_consensus_and_judge']} consensus rows "
              f"(kappa {r['human_judge_kappa']:.2f})")
        print(f"both humans say sendable: {r['both_humans_sendable']}")
        print("human disagreements:", r["human_disagreements"])
        print("judge disagreements:", r["judge_disagreements"])


if __name__ == "__main__":
    main()
