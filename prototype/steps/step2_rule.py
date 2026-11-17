"""Step 2 · Routing rule: who is allowed to decide this claim, before any model runs.

Rung 1 (rules). Pattern: routing on a rule. Trust level: set here, never by the model's confidence.
- out of scope or missing information  -> a person decides (L1), no model call;
- override switch off (AUTONOMY_ENABLED=false) -> the model may suggest, a person decides (L1);
- otherwise the model decides and step 4 sets the final level by money: L4 <= EUR 20, L2 up to EUR 100
  and every decline, L1 above EUR 100 or on any incoherence (policy v1.1, `src/agent/policy.py`).
Metric: share of claims sent to a person before the model (should stay small).

Owner (commit `step-2-rule`): Rania
"""
from src.agent.agent import autonomy_on


def rule(routed: dict, autonomy: bool | None = None) -> dict:
    autonomy = autonomy_on() if autonomy is None else autonomy
    if not routed["in_scope"]:
        return {"call_model": False, "autonomy": autonomy, "human_reason": routed["reason"]}
    return {"call_model": True, "autonomy": autonomy, "human_reason": ""}
