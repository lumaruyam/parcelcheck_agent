"""Step 3 · Decide: the fine-tuned Phi-3 applies the refund policy and writes the decision receipt.

Rung 3 -> 4: Phi-3-mini fine-tuned with LoRA on our synthetic claims (Vertex AI pipeline), served on a
Vertex AI endpoint. Without an endpoint the stub answers with the policy itself (demo and tests).
Pattern: prompt chaining (photo facts -> decision). Trust level: none on its own, only through step 4.
Fallback: endpoint down or undeployed -> no decision -> step 4 sends the claim to a person.
Metric: clause accuracy, valid JSON rate (`evals/report_v0.md`).

Owner (commit `step-3-decide`): Chanelle
"""
import json

from src.agent.agent import predict_endpoint, predict_stub


def decide(claim: dict, use_endpoint: bool) -> str:
    if not use_endpoint:
        return predict_stub(claim)
    try:
        return predict_endpoint(claim)
    except Exception as error:  # noqa: BLE001
        return json.dumps({"error": f"endpoint unavailable: {type(error).__name__}"})
