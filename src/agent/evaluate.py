"""Before/after evaluation: compare model predictions with the policy labels.

Usage: uv run python -m src.agent.evaluate data/test.jsonl predictions.jsonl
predictions.jsonl rows: {"case_id": ..., "raw_output": "<model text>"}
Prints the headline metrics for both courses (Workflow: accuracy; Product: money).
"""
import json
import sys

from src.agent.guardrail import check, parse


def main(test_path, pred_path):
    test = {r["case_id"]: r for r in map(json.loads, open(test_path))}
    preds = {r["case_id"]: r["raw_output"] for r in map(json.loads, open(pred_path))}
    n = len(test)
    valid = clause_ok = amount_ok = both_ok = 0
    auto = auto_wrong = 0
    over_refund = under_refund = 0.0
    wrong_refusals = 0
    for cid, row in test.items():
        t = row["target"]
        raw = preds.get(cid, "")
        d = parse(raw)
        g = check(row["input"], raw)
        if d:
            valid += 1
            c_ok = d["clause"] == t["clause"]
            try:
                a_ok = abs(float(d["amount_eur"]) - t["amount_eur"]) < 0.01
            except (TypeError, ValueError):
                a_ok = False
            clause_ok += c_ok
            amount_ok += a_ok
            both_ok += c_ok and a_ok
        if g["route"] == "auto":
            auto += 1
            paid = float(d["amount_eur"])
            if abs(paid - t["amount_eur"]) >= 0.01:
                auto_wrong += 1
                over_refund += max(0.0, paid - t["amount_eur"])
                under_refund += max(0.0, t["amount_eur"] - paid)
                if t["decision"] == "refund" and paid == 0:
                    wrong_refusals += 1
    def pct(x):
        return f"{100 * x / n:.1f}%"
    print(f"cases                      {n}")
    print(f"valid JSON                 {pct(valid)}")
    print(f"clause accuracy            {pct(clause_ok)}")
    print(f"amount exact               {pct(amount_ok)}")
    print(f"clause AND amount correct  {pct(both_ok)}   <- headline (Workflow)")
    print(f"auto-resolved (L4)         {pct(auto)}")
    print(f"wrong among auto-resolved  {auto_wrong}  (must be ~0: the guardrail's job)")
    print(f"over-refund leakage        €{over_refund:.2f}   <- counter-metric 1 (Product)")
    print(f"under-refund / wrong no    €{under_refund:.2f} · {wrong_refusals} cases   <- counter-metric 2")


if __name__ == "__main__":
    main(*sys.argv[1:3])
