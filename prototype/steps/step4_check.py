"""Step 4 · Policy check: recompute the amount from the rules, check coherence, set the final route.

Rung 1 (rules, `src/agent/guardrail.py`): the amount paid is always the policy's, never the model's.
Pattern: a verifier (not an evaluator-optimizer loop: on failure it hands over to a person, no retry).
Trust level: L4 only if every check passes and the amount is <= EUR 20; the override switch forces L1.
Metric: wrong automatic refunds (must be 0), share stopped by the guardrail.

Owner (commit `step-4-policy`): Wei-Ling
"""
from src.agent.guardrail import check as guardrail_check


def check(claim: dict, raw_output: str, autonomy: bool) -> dict:
    verdict = guardrail_check(claim, raw_output)
    reasons, route, trust = list(verdict["reasons"]), verdict["route"], verdict["trust_level"]
    if not autonomy:
        route, trust = "human", "L1_human_decides"
        reasons.append("override switch: AUTONOMY_ENABLED=false")
    decision = verdict["decision"] or {}
    if route == "auto" and decision.get("decision") == "refund":
        action = "refund_executed"
    elif route == "auto":
        action = "message_sent"
    else:
        action = "queued_for_human"
    return {"route": route, "reasons": reasons, "trust_level": trust, "decision": verdict["decision"], "action": action}
