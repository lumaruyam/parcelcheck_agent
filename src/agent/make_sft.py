"""Turn labelled cases into the CSV the course pipeline expects (one 'messages' column of JSON),
with a held-out test set that the team never trains or tunes on.

Usage: uv run python -m src.agent.make_sft data/cases.jsonl data/   (local check only;
the pipeline's data component builds the same prompt from cases.jsonl)
Writes: train.csv, test.csv (pipeline format) and test.jsonl (for evaluate.py)
"""
import json
import random
import sys

import pandas as pd

from src.agent.policy import CLAUSES

POLICY_TEXT = "\n".join(f"{k}: {v}" for k, v in CLAUSES.items())
INSTRUCTION = (
    "You are the refund agent of a shipping-label platform. Read the claim and the photo assessment, "
    "pick exactly one rule, compute the amount, and write a decision receipt.\n"
    f"Rules:\n{POLICY_TEXT}\n"
    'Answer with JSON only: {"clause": "R1".."R6", "decision": "refund"|"decline"|"need_evidence", '
    '"amount_eur": number, "receipt": "..."}\n\nClaim:\n'
)


def user_msg(inp: dict) -> str:
    return INSTRUCTION + json.dumps(inp, ensure_ascii=False)


def to_messages(row: dict) -> str:
    return json.dumps([{"role": "user", "content": user_msg(row["input"])},
                       {"role": "assistant", "content": json.dumps(row["target"], ensure_ascii=False)}],
                      ensure_ascii=False)


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2].rstrip("/")
    rows = [json.loads(line) for line in open(src)]
    random.Random(7).shuffle(rows)
    n_test = max(200, len(rows) // 7)
    test, train = rows[:n_test], rows[n_test:]
    pd.DataFrame({"messages": [to_messages(r) for r in train]}).to_csv(f"{out}/train.csv", index=False)
    pd.DataFrame({"messages": [to_messages(r) for r in test]}).to_csv(f"{out}/test.csv", index=False)
    with open(f"{out}/test.jsonl", "w") as f:
        for r in test:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"train {len(train)} · test {len(test)} -> {out}/train.csv, test.csv, test.jsonl")
