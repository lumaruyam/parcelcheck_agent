"""Session 3: score the decisions with the metrics that matter for a refund agent.

The course scored Yoda sentences with ragas string metrics (ROUGE, BLEU). A refund decision is
JSON with an amount, so string similarity says nothing useful: we score the decision itself and
the money, and recompute the policy amount like the guardrail does (src/agent/guardrail.py).
Kubeflow lightweight component: everything is defined inside the function.
"""
from kfp import dsl
from kfp.dsl import Dataset, Input, Metrics, Output

BASE_IMAGE = "python:3.11-slim"
PACKAGES = ["pandas==2.2.3"]


def evaluate_predictions(
    predictions: Input[Dataset],
    evaluation_results: Output[Dataset],
    metrics: Output[Metrics],
    auto_limit_eur: float = 20.0,
) -> None:
    """Per-claim scores -> evaluation_results.path (CSV); headline rates -> Kubeflow metrics."""
    import json
    import logging
    import re

    import pandas as pd

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("evaluation")

    def parse(text: str):
        m = re.search(r"\{.*\}", str(text), re.S)
        if not m:
            return None
        try:
            d = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
        return d if {"clause", "decision", "amount_eur", "receipt"} <= d.keys() else None

    def claim_from_prompt(user_input: str) -> dict:
        return json.loads(user_input.rsplit("Claim:\n", 1)[1])

    def policy_amount(clause: str, c: dict) -> float:
        if clause == "R1":
            return round(min(c["item_value_eur"], 25.0) + c["label_fee_eur"], 2)
        if clause == "R2":
            return round(min(c["item_value_eur"], 500.0) + c["label_fee_eur"], 2)
        if clause == "R3":
            return round(c["label_fee_eur"], 2)
        return 0.0

    def would_auto_pay(d: dict, c: dict) -> bool:
        """Simplified guardrail: coherent clause, exact policy amount, under the auto limit."""
        try:
            amount = float(d["amount_eur"])
        except (TypeError, ValueError):
            return False
        if d["clause"] not in {"R1", "R2", "R3"} or d["decision"] != "refund":  # declines and evidence requests go to a person
            return False
        if abs(amount - policy_amount(d["clause"], c)) > 0.01 or amount > auto_limit_eur:
            return False
        if d["clause"] in ("R1", "R2", "R3") and c["days_since_delivery"] > 7:
            return False
        if d["clause"] == "R2" and c["cover"] != "premium":
            return False
        if d["clause"] in ("R1", "R2") and c["fragile_item"] and not (c["fragile_option"] and c["padding"]):
            return False
        return True

    df = pd.read_csv(predictions.path).fillna("")
    rows = []
    for r in df.itertuples():
        ref = json.loads(r.reference)
        pred = parse(r.extracted_response)
        claim = claim_from_prompt(r.user_input)
        row = {"case_id": claim.get("case_id"), "ref_clause": ref["clause"], "ref_amount": ref["amount_eur"],
               "valid_json": pred is not None, "clause_ok": False, "amount_ok": False, "auto": False,
               "wrong_auto": False, "over_refund_eur": 0.0}
        if pred:
            row["pred_clause"] = pred.get("clause")
            row["clause_ok"] = pred.get("clause") == ref["clause"]
            try:
                paid = float(pred["amount_eur"])
                row["amount_ok"] = abs(paid - ref["amount_eur"]) < 0.01
            except (TypeError, ValueError):
                paid = None
            row["auto"] = would_auto_pay(pred, claim)
            if row["auto"] and paid is not None and not row["amount_ok"]:
                row["wrong_auto"] = True
                row["over_refund_eur"] = max(0.0, paid - ref["amount_eur"])
        rows.append(row)

    res = pd.DataFrame(rows)
    res.to_csv(evaluation_results.path, index=False)
    n = len(res)
    headline = {
        "valid_json_rate": res["valid_json"].mean(),
        "clause_accuracy": res["clause_ok"].mean(),
        "amount_exact_rate": res["amount_ok"].mean(),
        "clause_and_amount_rate": (res["clause_ok"] & res["amount_ok"]).mean(),  # headline (Workflow)
        "auto_resolved_rate": res["auto"].mean(),                                # L4 share (Product)
        "wrong_auto_count": float(res["wrong_auto"].sum()),                      # must be 0
        "over_refund_eur": float(res["over_refund_eur"].sum()),                  # counter-metric
        "n_cases": float(n),
    }
    for name, value in headline.items():
        metrics.log_metric(name, float(value))
        logger.info(f"{name}: {value:.4f}")


evaluation_component = dsl.component(
    func=evaluate_predictions,
    base_image=BASE_IMAGE,
    packages_to_install=PACKAGES,
)
