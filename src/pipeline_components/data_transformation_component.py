"""Session 2: turn the labelled claims (cases.jsonl) into the chat format, split train/test.

Kubeflow lightweight component: everything it uses is defined inside the function.
The prompt below must stay identical to src/agent/make_sft.py (tests/test_data_transformation.py checks it).
"""
from kfp import dsl

BASE_IMAGE = "python:3.11-slim"
PACKAGES = ["pandas==3.0.6", "gcsfs==2026.8.1", "fsspec==2026.7.0", "datasets==5.1.0", "pyarrow==26.0.0"]


def transform_data(
    raw_data_path: str,
    train_dataset_path: dsl.OutputPath("Dataset"),
    test_dataset_path: dsl.OutputPath("Dataset"),
    test_size: float = 0.15,
    seed: int = 42,
) -> None:
    """cases.jsonl -> train/test CSVs with one column "messages" (JSON list of {role, content})."""
    import json
    import logging

    import pandas as pd
    from datasets import Dataset

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("data_transformation")

    clauses = {
        "R1": "Content damaged in transit, standard cover: item value up to €25, plus the label fee.",
        "R2": "Content damaged in transit, premium cover: item value up to €500, plus the label fee.",
        "R3": "Packaging damaged, content intact: label fee refunded only.",
        "R4": "Claim filed more than 7 days after delivery: declined.",
        "R5": "Fragile item shipped without the fragile option or without padding: declined.",
        "R6": "No damage visible or photo unusable: more evidence requested, a person decides.",
    }
    policy_text = "\n".join(f"{k}: {v}" for k, v in clauses.items())
    instruction = (
        "You are the refund agent of a shipping-label platform. Read the claim and the photo assessment, "
        "pick exactly one rule, compute the amount, and write a decision receipt.\n"
        f"Rules:\n{policy_text}\n"
        'Answer with JSON only: {"clause": "R1".."R6", "decision": "refund"|"decline"|"need_evidence", '
        '"amount_eur": number, "receipt": "..."}\n\nClaim:\n'
    )

    logger.info(f"Reading raw data from {raw_data_path}")
    df = pd.read_json(raw_data_path, lines=True)
    logger.info(f"Loaded {len(df)} claims; clauses: {df['target'].apply(lambda t: t['clause']).value_counts().to_dict()}")

    def format_row(row: dict) -> dict:
        return {
            "messages": [
                {"role": "user", "content": instruction + json.dumps(row["input"], ensure_ascii=False)},
                {"role": "assistant", "content": json.dumps(row["target"], ensure_ascii=False)},
            ]
        }

    dataset = Dataset.from_pandas(df[["input", "target"]])
    dataset = dataset.map(format_row, remove_columns=dataset.column_names)
    logger.info(f"Example formatted row: {dataset[0]['messages'][1]}")

    splits = dataset.train_test_split(test_size=test_size, seed=seed)
    logger.info(f"Train size: {len(splits['train'])}, test size: {len(splits['test'])}")

    for split_name, output_path in (("train", train_dataset_path), ("test", test_dataset_path)):
        output = splits[split_name].to_pandas()
        output["messages"] = output["messages"].apply(lambda m: json.dumps(list(m), ensure_ascii=False))
        output.to_csv(output_path, index=False)
        logger.info(f"Wrote {len(output)} {split_name} rows to {output_path}")


data_transformation_component = dsl.component(
    func=transform_data,
    base_image=BASE_IMAGE,
    packages_to_install=PACKAGES,
)
