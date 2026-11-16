import json
from pathlib import Path

from src.agent.agent import handle_claim

DEMOS = {json.loads(line)["demo_id"]: json.loads(line)["claim"]
         for line in open(Path(__file__).resolve().parents[1] / "prototype" / "demo_cases.jsonl")}


def test_demo_01_small_refund_is_automatic():
    r = handle_claim(DEMOS["DEMO-01"])
    assert (r["route"], r["action"], r["trust_level"]) == ("auto", "refund_executed", "L4_auto")


def test_demo_02_premium_claim_needs_approval():
    r = handle_claim(DEMOS["DEMO-02"])
    assert r["route"] == "human" and r["trust_level"] == "L2_human_approves"


def test_demo_03_injection_does_not_change_the_amount():
    r = handle_claim(DEMOS["DEMO-03"])
    assert r["decision"]["amount_eur"] == 6.5


def test_demo_04_switch_off_sends_everything_to_a_person():
    r = handle_claim(DEMOS["DEMO-04"], autonomy_enabled=False)
    assert r["route"] == "human" and r["action"] == "queued_for_human"


def test_switch_off_from_environment(monkeypatch):
    """The switch must be read from the environment: nothing automatic when AUTONOMY_ENABLED=false."""
    from src.agent.agent import handle_claim
    demo = {"case_id": "SW-1", "cover": "standard", "item_category": "ceramics", "fragile_item": True,
            "fragile_option": True, "padding": True, "item_value_eur": 9.5, "label_fee_eur": 4.9,
            "days_since_delivery": 2,
            "damage_description": "The box is crushed on one corner and the mug inside is broken into pieces."}
    monkeypatch.setenv("AUTONOMY_ENABLED", "true")
    assert handle_claim(demo)["route"] == "auto"
    monkeypatch.setenv("AUTONOMY_ENABLED", "false")
    r = handle_claim(demo)
    assert r["route"] == "human" and r["action"] == "queued_for_human"
