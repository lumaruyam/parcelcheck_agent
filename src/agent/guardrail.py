"""Safety check between the model and the money. Nothing is refunded unless every check passes.

Input: the case (as the model saw it), the damage description, and the model's raw output.
Output: {"route": "auto" | "human", "reasons": [...], "trust_level": ..., "decision": parsed or None}
"""
import json
import re

from src.agent.policy import AUTO_LIMIT_EUR, CLAIM_WINDOW_DAYS, CLAUSES, trust_level

NO_DAMAGE_WORDS = re.compile(r"no damage|undamaged|intact|parfait état|too dark|blurry|cannot be determined", re.I)


def parse(raw: str):
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return d if {"clause", "decision", "amount_eur", "receipt"} <= d.keys() else None


def check(case_input: dict, raw_output: str, true_damage_type: str | None = None) -> dict:
    reasons = []
    d = parse(raw_output)
    if d is None:
        return {"route": "human", "reasons": ["output is not valid decision JSON"], "trust_level": "L1_human_decides", "decision": None}
    if d["clause"] not in CLAUSES:
        reasons.append(f"unknown clause {d['clause']}")
    try:
        amount = float(d["amount_eur"])
    except (TypeError, ValueError):
        amount = None
        reasons.append("amount is not a number")
    # recompute what the policy allows for the clause the model chose
    if amount is not None and d["clause"] in CLAUSES:
        cap = {"R1": 25.0, "R2": 500.0}.get(d["clause"])
        if d["clause"] in ("R1", "R2"):
            allowed = round(min(case_input["item_value_eur"], cap) + case_input["label_fee_eur"], 2)
        elif d["clause"] == "R3":
            allowed = round(case_input["label_fee_eur"], 2)
        else:
            allowed = 0.0
        if abs(amount - allowed) > 0.01:
            reasons.append(f"amount €{amount:.2f} does not match clause {d['clause']} (policy gives €{allowed:.2f})")
    # coherence between facts and clause
    if d["clause"] in ("R1", "R2", "R3") and case_input["days_since_delivery"] > CLAIM_WINDOW_DAYS:
        reasons.append("refund outside the 7-day claim window")
    if d["clause"] in ("R1", "R2") and case_input["fragile_item"] and not (case_input["fragile_option"] and case_input["padding"]):
        reasons.append("fragile item without fragile option or padding: rule R5 should apply")
    if d["clause"] == "R2" and case_input["cover"] != "premium":
        reasons.append("premium clause on a standard-cover parcel")
    if d["clause"] in ("R1", "R2") and NO_DAMAGE_WORDS.search(case_input["damage_description"]):
        reasons.append("content-damage refund but the photo description says no damage / unclear")
    if d["decision"] == "need_evidence":
        reasons.append("more evidence requested: a person decides")
    if d["decision"] == "decline":
        reasons.append("every decline is approved by a person (spec.md, trust levels)")
    if amount and str(d["amount_eur"]) not in d["receipt"] and f"{amount:.2f}" not in d["receipt"]:
        reasons.append("receipt does not state the amount")
    if d["clause"] not in d["receipt"]:
        reasons.append("receipt does not cite the clause")
    lvl = trust_level(amount or 0.0)
    if amount is not None and amount > AUTO_LIMIT_EUR:
        reasons.append(f"amount above €{AUTO_LIMIT_EUR:.0f}: {lvl}")
    # the trust level a claim actually gets (governance.md, Session 3 table), not only the money band:
    # a decline is approved by a person (L2); more evidence or any incoherence -> a person decides (L1)
    band_or_decline = {f"amount above €{AUTO_LIMIT_EUR:.0f}: {lvl}", "every decline is approved by a person (spec.md, trust levels)"}
    if any(r not in band_or_decline for r in reasons):
        lvl = "L1_human_decides"
    elif d["decision"] == "decline" and lvl == "L4_auto":
        lvl = "L2_human_approves"
    return {"route": "human" if reasons else "auto", "reasons": reasons, "trust_level": lvl, "decision": d}
