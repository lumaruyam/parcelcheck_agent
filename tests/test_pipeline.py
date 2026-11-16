"""The four-step prototype must decide exactly like the agent used for the eval (same rules, same routes)."""
import csv

from prototype.pipeline import run
from scripts.run_eval_set import parse_row
from src.agent.agent import handle_claim


def test_pipeline_matches_agent_on_eval_rows():
    rows = list(csv.DictReader(open("evals/eval_set_v0.csv", encoding="utf-8")))
    checked = 0
    for row in rows:
        claim = parse_row(row["input_the_agent_receives"])
        if not claim:
            continue
        a, b = handle_claim(claim, autonomy_enabled=True), run(claim, autonomy=True)
        assert (a["route"], a["action"], a["decision"]) == (b["route"], b["action"], b["decision"]), row["id"]
        checked += 1
    assert checked >= 40


def test_out_of_scope_goes_to_a_person_without_the_model():
    claim = {"case_id": "X", "cover": "standard", "item_category": "books", "fragile_item": False,
             "fragile_option": False, "padding": True, "item_value_eur": 12.0, "label_fee_eur": 4.9,
             "days_since_delivery": 2, "damage_description": "The parcel never arrived."}
    r = run(claim)
    assert r["route"] == "human" and r["model_output"] is None and r["trust_level"] == "L1_human_decides"
