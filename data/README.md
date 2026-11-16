# data/

Small synthetic files only. Real photos and anything about real customers never go in Git.

| File | What | How it is made |
|---|---|---|
| `cases.jsonl` | 1,500 synthetic damaged-parcel claims, each labelled by `src/agent/policy.py` (clause, decision, amount, receipt) | `uv run python -m src.agent.generate_cases --n 1500 --seed 42 --out data/cases.jsonl` (add `--paraphrase-with-gemini` for wording variety) |
| `cases_v3.jsonl` (not in Git) | 1,477 rows: 1,300 v1-template claims + 177 rows from real photos (Roboflow D4, CC BY 4.0) described by Gemini 3.8 Flash. Superseded by v4 before any training, so the file is not kept in Git | rebuild (free, uses `photo_descriptions.jsonl`): `scripts/build_photo_training_data.py --source <D4 folder> --exclude-class food --photo-r6-ratio 0.5 --n-templates 1300 --out data/cases_v3.jsonl` |
| `cases_v4.jsonl` | Same 177 photo rows + 1,300 claims from templates v4 (`src/agent/templates_v4.py`: separate EN/FR, damage that fits the item, ~1,270 unique descriptions, 41% French). Rows too close to an eval photo text are redrawn | same command + `--templates v4 --out data/cases_v4.jsonl` |
| `photo_descriptions.jsonl` | Gemini's description of each training photo (cache, so rebuilds cost nothing). No test photo: excluded by name and perceptual hash | written by `build_photo_training_data.py` |

v2 (8 Nov plan: R5 boost + Gemini rewrites of the templates) was never built; v3 and v4 cover both goals. Before freezing an eval set: `python -m scripts.check_eval_leak --eval evals/<file>.csv`.

Upload before running the pipeline:

```bash
gsutil cp data/cases.jsonl gs://$GCP_BUCKET_NAME/data/cases.jsonl
gcloud storage cp data/cases_v4.jsonl gs://$GCP_BUCKET_NAME/data/   # v4
```

The pipeline splits 85% train / 15% test (seed 42). The test split is never used to tune prompts or hyper-parameters.

The Product eval-set (`evals/eval_set_v0.csv`) is separate: hand-checked cases, never used for training. The demo claims (`prototype/demo_cases.jsonl`) are never in either set.
