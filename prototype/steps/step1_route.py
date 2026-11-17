"""Step 1 · Router: read the claim and its evidence; decide whether it is a damaged-parcel claim at all.

Rung 3 for the photo (pretrained Gemini 3.8 Flash describes it, facts only: `src/agent/vision.py`),
rung 1 for the scope (keywords). Pattern: routing. Trust level: no autonomy, it only labels.
Metric: share of claims routed out of scope; photo test in `evals/photo_report_v1.md`.

Owner (commit `step-1-router`): Luli
"""
import re

OUT_OF_SCOPE = re.compile(
    r"never arrived|not delivered|was lost|lost parcel|stolen|wrong item|missing item|"
    r"jamais reçu|pas reçu|jamais arrivé|perdu|volé", re.I)
REQUIRED = ("cover", "item_category", "item_value_eur", "label_fee_eur", "days_since_delivery", "damage_description")


def route(claim: dict, photo_path: str | None = None) -> dict:
    """-> {"in_scope": bool, "reason": str, "claim": claim with damage_description filled}."""
    claim = dict(claim)
    if photo_path and not claim.get("damage_description"):
        from src.agent.vision import describe  # Gemini, facts only
        claim["damage_description"] = describe(photo_path)
    missing = [k for k in REQUIRED if claim.get(k) in (None, "")]
    if missing:
        return {"in_scope": False, "reason": "missing information: " + ", ".join(missing), "claim": claim}
    text = f"{claim.get('merchant_message', '')} {claim['damage_description']}"
    if OUT_OF_SCOPE.search(text):
        return {"in_scope": False, "reason": "not a damaged-parcel claim (lost, stolen or wrong item)", "claim": claim}
    return {"in_scope": True, "reason": "", "claim": claim}
