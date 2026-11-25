# Eval report v1 · ParcelCheck (P4) · 25 Nov 2026

> Eval set `evals/eval_set_v1.csv` (100 claims, leak-checked, labels checked by hand 20 Nov). Model: fine-tuned Phi-3 + LoRA, Model Registry `parcelcheck-phi-3-mini` **version 2**, Vertex AI endpoint `europe-west2` (n1-standard-8 + 1 × T4), deployed 25 Nov 14:51 → undeployed after the run (≈ 6 h, ≈ $6). Command: `uv run python -m scripts.run_eval_set --endpoint --file evals/eval_set_v1.csv`. Raw outputs: `evals/runs/20261125-2030_endpoint.jsonl`. Run by Wei-Ling.

## 1 · Headline

| | Criterion | Eval v0 (7 Nov, 48 claims) | **Eval v1, as run** | **Eval v1, R3 guardrail fix** |
|---|---|---|---|---|
| Decided alone (L4), of decidable claims R1–R3 | ≥ 40 % | 39 % | **18 %** (7 of 40) | **10 %** (4 of 40) |
| Wrong automatic refunds | **0** | 0 | **3** | **0** |
| Hand-over agrees with the label | — | 46 / 48 | 80 / 90 | 83 / 90 |
| Right clause | — | 92 % | 64 % (58 / 90) | 64 % |
| Valid JSON | — | 96 % | 100 % (90 / 90) | 100 % |

**The criterion is not met.** The model is safe once the guardrail is fixed (0 wrong automatic refunds) but decides alone far less often than eval v0 suggested. Eval v0 was optimistic: 31 of its 48 photo texts had been seen in training (`spec.md` row 10). Eval v1 is new and leak-checked, so **v1 is the number to trust**.

10 of the 100 rows (V091–V100) are skipped by the harness: they have no clause label to score against. The "R3 guardrail fix" column replays the saved outputs through the fixed guardrail (`src/agent/guardrail.py`, PR No.31); the model was not called again.

## 2 · Where the model is wrong (expected clause → predicted clause, 90 claims)

| Expected | Rows | Right | Wrong as |
|---|---|---|---|
| R1 standard damage | 22 | **22** | — |
| R2 premium damage | 8 | **8** | — |
| R3 packaging only (label fee) | 10 | 4 | R1 × 6 |
| R4 outside the 7-day window | 8 | **8** | — |
| R5 fragile without option or padding | 12 | **0** | R1 × 9, R2 × 3 |
| R6 no damage visible / photo unusable | 30 | 16 | R1 × 10, R3 × 3, R2 × 1 |

- **R5 is never predicted** and **R6 is often missed**: these two clauses are rare in the training data (data v4) and most v1 rows for R6 are real public photos, unlike the template sentences of training.
- Most R1 refunds are above €20, so they go to a person by design (L2): the L4 ceiling on this set is set by the €20 limit, not only by the model.

## 3 · The three wrong automatic refunds and the fix

| Claim | Photo (Gemini description) | Model | Label |
|---|---|---|---|
| V075 | open box and jacket, "intact and undamaged" | R3, refund €6.50 | R6, €0 |
| V076 | three sealed boxes, "intact condition with no signs of damage" | R3, refund €4.90 | R6, €0 |
| V082 | a wooden box, "does not show a shipping parcel" | R3, refund €12.40 | R6, €0 |

Cause: the guardrail checked "the photo says no damage → a person decides" for R1 and R2 only; R3 refunds are under €20, so they went through. **Fix (PR No.31):** an R3 refund now needs visible packaging damage in the photo description; intact or unclear → a person (R6). Replayed on the saved outputs: the three are held, the four correct R3 refunds still pass, and no correct R3 row of eval v0 or v1 is held. Two tests in `tests/test_policy_guardrail.py`.

Of the **32 claims with a wrong clause** (§2), the guardrail sent **29 to a person** before the fix and **32 of 32** after: these three were the only wrong decisions paid automatically.

## 4 · What we do next
1. **Retrain** with more R5 and R6 cases, including real-photo descriptions (Roboflow, CC BY 4.0) next to the template sentences; re-run eval v1 unchanged.
2. **The launch gate stays closed** (`08_launch_memo.md` §3, condition 2): the AI module stays in staging; shadow mode starts only when eval v1 shows ≥ 40 % L4 with 0 wrong automatic refunds.
3. **Judge rates:** the receipts to grade now exist (this run). Grading sheet: `uv run python -m scripts.judge_kit sheet --eval evals/eval_set_v1.csv`; graders Luli and Rania; not done before the `v1.0` tag.
