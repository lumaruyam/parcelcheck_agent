"""The agent, end to end: claim (+ photo description) -> fine-tuned Phi-3 -> guardrail -> route.

The model call is pluggable:
- `predict_endpoint`: the Vertex AI endpoint deployed in Session 4 (REST call, like the course app);
- `predict_stub`: no cloud at all, answers with the policy's own decision (for demos and tests).

The override switch (governance.md, Session 4): with AUTONOMY_ENABLED=false nothing is paid
automatically, every claim goes to a person.
"""
from __future__ import annotations

import json
import re
import subprocess

import requests

from src.agent.guardrail import check
from src.agent.make_sft import user_msg
from src.agent.policy import Case, decide

GENERATION_PARAMETERS = {"max_new_tokens": 256, "do_sample": False}


def build_prompt(claim: dict) -> str:
    """Phi-3 chat template written by hand (the app does not load a tokenizer)."""
    return f"<|user|>\n{user_msg(claim)}<|end|>\n<|assistant|>\n"


def extract_response(generated_text: str) -> str:
    match = re.search(r"<\|assistant\|>(.*?)(?:<\|end\|>|<\|endoftext\|>|$)", generated_text, re.DOTALL)
    return match.group(1).strip() if match else generated_text.strip()


def get_access_token() -> str:
    """gcloud user token: fine for a demo; production would use a service account."""
    return subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()


def predict_endpoint(claim: dict) -> str:
    from src.constants import ENDPOINT_URL

    payload = {"instances": [{"input": build_prompt(claim)}], "parameters": GENERATION_PARAMETERS}
    r = requests.post(ENDPOINT_URL, json=payload, timeout=120,
                      headers={"Authorization": f"Bearer {get_access_token()}", "Content-Type": "application/json"})
    r.raise_for_status()
    pred = r.json()["predictions"][0]
    if isinstance(pred, dict):  # our handler returns {"response", "generated_text"}
        return pred.get("response") or extract_response(pred.get("generated_text", ""))
    return extract_response(str(pred))


def predict_stub(claim: dict) -> str:
    """Offline stand-in: the policy's answer, as the fine-tuned model should write it."""
    text = claim["damage_description"].lower()
    unclear = ("too dark", "blurry", "cannot be determined", "not visible", "does not show", "only part of")
    no_damage = ("no damage is visible", "look normal", "looks new", "look new", "appears new", "clean box")
    intact_item = ("intact", "undamaged", "parfait état", "is fine", "looks fine", "no damage")
    if any(w in text for w in unclear + no_damage):
        dtype = "unclear_photo"          # R6: a person decides
    elif any(w in text for w in intact_item):
        dtype = "packaging_only"
    else:
        dtype = "content_damaged"
    fields = {k: claim[k] for k in Case.__dataclass_fields__ if k in claim}
    d = decide(Case(**fields, damage_type=dtype))
    head = (f"Refund approved: €{d['amount_eur']:.2f}." if d["decision"] == "refund"
            else "Refund declined." if d["decision"] == "decline" else "More evidence needed before a decision.")
    return json.dumps({**d, "receipt": f"{head} Rule {d['clause']}. Photo assessment: \"{claim['damage_description']}\""},
                      ensure_ascii=False)


def autonomy_on() -> bool:
    """Read the switch on every claim, so flipping it needs no deploy and no restart (governance.md, S4)."""
    import os
    return os.getenv("AUTONOMY_ENABLED", "true").strip().lower() == "true"


def handle_claim(claim: dict, predict=predict_stub, autonomy_enabled: bool | None = None) -> dict:
    if autonomy_enabled is None:  # bug found by the switch test on 7 Nov: the switch was never read
        autonomy_enabled = autonomy_on()
    raw = predict(claim)
    verdict = check(claim, raw)
    reasons = list(verdict["reasons"])
    route = verdict["route"]
    trust = verdict["trust_level"]
    if not autonomy_enabled:
        route = "human"
        trust = "L1_human_decides"  # the switch drops the whole system to L1 (04_architecture.md §4)
        reasons.append("override switch: AUTONOMY_ENABLED=false")
    decision = verdict["decision"] or {}
    if route == "auto" and decision.get("decision") == "refund":
        action = "refund_executed"
    elif route == "auto":
        action = "message_sent"
    else:
        action = "queued_for_human"
    return {"claim": claim, "model_output": raw, "route": route, "reasons": reasons,
            "trust_level": trust, "decision": verdict["decision"], "action": action}


if __name__ == "__main__":
    demo = {"case_id": "DEMO-01", "cover": "standard", "item_category": "ceramics", "fragile_item": True,
            "fragile_option": True, "padding": True, "item_value_eur": 9.5, "label_fee_eur": 4.9,
            "days_since_delivery": 2,
            "damage_description": "The box is crushed on one corner and the mug inside is broken into pieces."}
    print(json.dumps(handle_claim(demo), indent=2, ensure_ascii=False))
