import json

from src.agent.guardrail import check
from src.agent.policy import Case, decide, trust_level

BASE = dict(case_id="T1", cover="standard", item_category="ceramics", fragile_item=True, fragile_option=True,
            padding=True, item_value_eur=40.0, label_fee_eur=4.9, days_since_delivery=2,
            damage_description="The box is crushed and the mug inside is broken.")


def test_standard_cover_is_capped_at_25_plus_fee():
    assert decide(Case(**BASE, damage_type="content_damaged")) == {"clause": "R1", "decision": "refund", "amount_eur": 29.9}


def test_late_claim_is_declined():
    assert decide(Case(**{**BASE, "days_since_delivery": 9}, damage_type="content_damaged"))["clause"] == "R4"


def test_fragile_without_option_is_declined():
    assert decide(Case(**{**BASE, "fragile_option": False}, damage_type="content_damaged"))["clause"] == "R5"


def test_trust_levels():
    assert trust_level(20.0) == "L4_auto"
    assert trust_level(20.01) == "L2_human_approves"
    assert trust_level(100.01) == "L1_human_decides"


def test_guardrail_blocks_a_wrong_amount():
    raw = json.dumps({"clause": "R1", "decision": "refund", "amount_eur": 300, "receipt": "Refund €300. Rule R1."})
    verdict = check(BASE, raw)
    assert verdict["route"] == "human"
    assert any("does not match clause" in r for r in verdict["reasons"])


def test_guardrail_sends_invalid_json_to_a_person():
    assert check(BASE, "sure, refund it")["route"] == "human"


def test_guardrail_lets_a_correct_small_refund_through():
    claim = {**BASE, "item_value_eur": 9.5}
    raw = json.dumps({"clause": "R1", "decision": "refund", "amount_eur": 14.4, "receipt": "Refund approved: €14.40. Rule R1."})
    assert check(claim, raw)["route"] == "auto"
