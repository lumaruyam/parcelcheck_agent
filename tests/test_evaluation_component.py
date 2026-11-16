import json
from types import SimpleNamespace

import pandas as pd

from src.agent.make_sft import user_msg
from src.pipeline_components.evaluation_component import evaluate_predictions


class FakeMetrics(SimpleNamespace):
    def log_metric(self, name, value):
        self.values[name] = value


def test_scores_decisions_and_money(tmp_path):
    claim = {"case_id": "E1", "cover": "standard", "item_category": "books", "fragile_item": False,
             "fragile_option": False, "padding": True, "item_value_eur": 10.0, "label_fee_eur": 4.9,
             "days_since_delivery": 2, "damage_description": "Book torn in half."}
    ref = {"clause": "R1", "decision": "refund", "amount_eur": 14.9, "receipt": "Refund approved: €14.90. Rule R1."}
    good = json.dumps(ref)
    bad = json.dumps({**ref, "amount_eur": 19.0, "receipt": "Refund approved: €19.00. Rule R1."})
    preds = pd.DataFrame([{"user_input": user_msg(claim), "reference": json.dumps(ref), "extracted_response": r}
                          for r in (good, bad, "not json")])
    p = tmp_path / "preds.csv"
    preds.to_csv(p, index=False)
    m = FakeMetrics(values={})
    evaluate_predictions(SimpleNamespace(path=str(p)), SimpleNamespace(path=str(tmp_path / "res.csv")), m)
    assert abs(m.values["clause_and_amount_rate"] - 1 / 3) < 1e-9
    assert abs(m.values["valid_json_rate"] - 2 / 3) < 1e-9
    assert m.values["wrong_auto_count"] == 0  # the wrong amount does not match the policy, so it is not paid
