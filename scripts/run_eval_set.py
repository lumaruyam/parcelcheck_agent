"""Run the agent on the Product eval-set and print the numbers for evals/report_v0.md (Session 4).

    uv run python -m scripts.run_eval_set                 # stub model: the routing upper bound
    uv run python -m scripts.run_eval_set --endpoint      # the fine-tuned model on Vertex AI (the real number)

Never tune the prompt while looking at this file's output (spec.md §9): change the spec, then re-run.
"""
import argparse
import csv
import re

from prototype.pipeline import run as run_pipeline  # the four steps (prototype/README.md)
from src.agent.agent import autonomy_on, predict_endpoint, predict_stub

PATTERN = re.compile(
    r"Claim (?P<case_id>\S+): cover (?P<cover>\w+), (?P<item_category>[\w ]+) \(fragile (?P<fragile_item>\w+), "
    r"fragile option (?P<fragile_option>\w+), padding (?P<padding>\w+)\), declared value €(?P<item_value_eur>[\d.]+), "
    r"label fee €(?P<label_fee_eur>[\d.]+), (?P<days>\d+) days after delivery\..*?Photo: \"(?P<photo>.*?)\""
)


def parse_row(text: str) -> dict | None:
    m = PATTERN.search(text)
    if not m:
        return None
    g = m.groupdict()
    return {"case_id": g["case_id"].rstrip(":"), "cover": g["cover"], "item_category": g["item_category"].strip(),
            "fragile_item": g["fragile_item"] == "True", "fragile_option": g["fragile_option"] == "True",
            "padding": g["padding"] == "True", "item_value_eur": float(g["item_value_eur"]),
            "label_fee_eur": float(g["label_fee_eur"]), "days_since_delivery": int(g["days"]),
            "damage_description": g["photo"]}


def expected(row: dict) -> tuple[str, float]:
    m = re.search(r"clause (R\d) · €([\d.]+)", row["expected_output_or_action"])
    return (m.group(1), float(m.group(2))) if m else ("", 0.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="evals/eval_set_v0.csv")
    ap.add_argument("--endpoint", action="store_true")
    a = ap.parse_args()
    predict = predict_endpoint if a.endpoint else predict_stub
    rows = list(csv.DictReader(open(a.file, encoding="utf-8")))
    n = decidable = auto = wrong_auto = handover_agree = skipped = 0
    misses, raws = [], []
    for row in rows:
        claim = parse_row(row["input_the_agent_receives"])
        clause, amount = expected(row)
        if not claim or not clause:
            skipped += 1
            continue
        n += 1
        r = run_pipeline(claim, predict=predict)
        raws.append({"id": row["id"], "route": r["route"], "reasons": r["reasons"], "raw": r["model_output"]})
        d = r["decision"] or {}
        is_auto = r["route"] == "auto"
        auto += is_auto
        decidable += clause in ("R1", "R2", "R3")
        if is_auto and abs(float(d.get("amount_eur", -1)) - amount) > 0.01:
            wrong_auto += 1
        expected_handover = row["hand_over_to_a_person"].startswith("yes")
        handover_agree += expected_handover == (not is_auto)
        if d.get("clause") != clause:
            misses.append((row["id"], clause, d.get("clause"), "; ".join(r["reasons"])[:80]))
    print(f"model                       {'Vertex AI endpoint' if a.endpoint else 'policy stub (upper bound)'}")
    print(f"AUTONOMY_ENABLED            {autonomy_on()}")
    print(f"cases scored / skipped      {n} / {skipped}")
    print(f"auto-resolved (L4)          {auto} ({100 * auto / max(n, 1):.0f}% of all, {100 * auto / max(decidable, 1):.0f}% of decidable R1-R3)")
    print(f"wrong automatic refunds     {wrong_auto}   <- must be 0")
    print(f"hand-over agrees with label {handover_agree}/{n}")
    print("clause misses (id, expected, got, guardrail reasons):")
    for m in misses:
        print("  ", m)
    # keep every raw output, so a miss can be read later without redeploying (report_v0.md §3)
    import json
    import os
    from datetime import datetime
    os.makedirs("evals/runs", exist_ok=True)
    tag = ("endpoint" if a.endpoint else "stub") + ("" if autonomy_on() else "_switch-off")
    path = f"evals/runs/{datetime.now():%Y%m%d-%H%M}_{tag}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for x in raws:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"raw outputs saved to {path}")


if __name__ == "__main__":
    main()
