"""ParcelCheck prototype: the four steps chained (Assignment 4). Used by the Chainlit app and the eval.

    claim -> [1 route] -> [2 rule] -> [3 decide] -> [4 check] -> paid (L4) or a person (L2 / L1)

    uv run python -m prototype.pipeline        # runs the four demo claims
"""
import json
from pathlib import Path

from prototype.steps.step1_route import route
from prototype.steps.step2_rule import rule
from prototype.steps.step3_decide import decide
from prototype.steps.step4_check import check


def run(claim: dict, use_endpoint: bool = False, autonomy: bool | None = None,
        photo_path: str | None = None, predict=None) -> dict:
    routed = route(claim, photo_path)
    plan = rule(routed, autonomy)
    claim = routed["claim"]
    if not plan["call_model"]:
        return {"claim": claim, "model_output": None, "route": "human", "reasons": [plan["human_reason"]],
                "trust_level": "L1_human_decides", "decision": None, "action": "queued_for_human"}
    raw = predict(claim) if predict else decide(claim, use_endpoint)
    result = check(claim, raw, plan["autonomy"])
    return {"claim": claim, "model_output": raw, **result}


if __name__ == "__main__":
    for line in open(Path(__file__).parent / "demo_cases.jsonl"):
        demo = json.loads(line)
        r = run(demo["claim"], autonomy=False if demo["demo_id"] == "DEMO-04" else None)
        print(demo["demo_id"], r["route"], r["trust_level"], r["action"], (r["decision"] or {}).get("amount_eur"))
