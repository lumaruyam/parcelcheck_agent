"""Refund policy for damaged parcels (invented for the project, v1).

This module is the single source of truth: it labels the training data, and the
guardrail uses it to recompute every amount the model proposes.
"""
from dataclasses import dataclass

AUTO_LIMIT_EUR = 20.0          # L4: the agent acts alone at or under this amount
HUMAN_REVIEW_LIMIT_EUR = 100.0 # L2 between 20 and 100 (a person approves); L1 above
CLAIM_WINDOW_DAYS = 7
STANDARD_COVER_EUR = 25.0
PREMIUM_COVER_EUR = 500.0

# damage_type is what the model must infer from Gemini's free-text description
DAMAGE_TYPES = ["content_damaged", "packaging_only", "no_visible_damage", "unclear_photo"]

CLAUSES = {
    "R1": "Content damaged in transit, standard cover: item value up to €25, plus the label fee.",
    "R2": "Content damaged in transit, premium cover: item value up to €500, plus the label fee.",
    "R3": "Packaging damaged, content intact: label fee refunded only.",
    "R4": "Claim filed more than 7 days after delivery: declined.",
    "R5": "Fragile item shipped without the fragile option or without padding: declined.",
    "R6": "No damage visible or photo unusable: more evidence requested, a person decides.",
}


@dataclass
class Case:
    case_id: str
    cover: str              # "standard" | "premium"
    item_category: str      # e.g. "ceramics", "electronics", "clothing"
    fragile_item: bool
    fragile_option: bool    # merchant paid the fragile option
    padding: bool           # merchant used padding (per label metadata / photo)
    item_value_eur: float
    label_fee_eur: float
    days_since_delivery: int
    damage_type: str        # ground truth; the model only sees the description
    damage_description: str # what Gemini wrote about the photo


def decide(c: Case) -> dict:
    """Return the correct decision for a case: clause, decision, amount_eur."""
    if c.damage_type in ("no_visible_damage", "unclear_photo"):
        return {"clause": "R6", "decision": "need_evidence", "amount_eur": 0.0}
    if c.days_since_delivery > CLAIM_WINDOW_DAYS:
        return {"clause": "R4", "decision": "decline", "amount_eur": 0.0}
    if c.damage_type == "packaging_only":
        return {"clause": "R3", "decision": "refund", "amount_eur": round(c.label_fee_eur, 2)}
    # content damaged
    if c.fragile_item and (not c.fragile_option or not c.padding):
        return {"clause": "R5", "decision": "decline", "amount_eur": 0.0}
    cap = PREMIUM_COVER_EUR if c.cover == "premium" else STANDARD_COVER_EUR
    clause = "R2" if c.cover == "premium" else "R1"
    return {"clause": clause, "decision": "refund",
            "amount_eur": round(min(c.item_value_eur, cap) + c.label_fee_eur, 2)}


def trust_level(amount_eur: float) -> str:
    if amount_eur <= AUTO_LIMIT_EUR:
        return "L4_auto"
    if amount_eur <= HUMAN_REVIEW_LIMIT_EUR:
        return "L2_human_approves"
    return "L1_human_decides"
