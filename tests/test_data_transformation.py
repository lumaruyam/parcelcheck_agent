import json

import pandas as pd

from src.agent.make_sft import user_msg
from src.pipeline_components.data_transformation_component import transform_data


def test_component_writes_chat_format_and_matches_the_app_prompt(tmp_path):
    rows = [json.loads(line) for line in open("data/cases.jsonl")][:40]
    raw = tmp_path / "cases.jsonl"
    raw.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
    train, test = tmp_path / "train.csv", tmp_path / "test.csv"

    transform_data(str(raw), str(train), str(test), test_size=0.25, seed=42)

    tr, te = pd.read_csv(train), pd.read_csv(test)
    assert len(tr) + len(te) == 40 and len(te) == 10
    messages = json.loads(tr["messages"][0])
    assert [m["role"] for m in messages] == ["user", "assistant"]
    claim = json.loads(messages[0]["content"].rsplit("Claim:\n", 1)[1])
    # no drift between the training prompt and the prompt the app sends
    assert messages[0]["content"] == user_msg(claim)
    assert set(json.loads(messages[1]["content"])) == {"clause", "decision", "amount_eur", "receipt"}
