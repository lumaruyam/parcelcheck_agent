# evals/ — eval-set, grading guideline and the two agreement rates · ParcelCheck (P4)

> Assignment 5 §5 ("make the judge trustworthy"). Guideline written **13 Nov 2026, before anyone grades**. The rates below are filled from `scripts/judge_kit.py score`, never by hand.

## What is in this folder

| File | What | Owner |
|---|---|---|
| `eval_set_v0.csv` | 50 labelled claims, frozen (the 7 Nov run, `report_v0.md`); hand check 50/50 (Luli, 11 Nov) | frozen |
| `eval_set_v1.csv` | 100 claims (200 optional), stratified by segment, synthetic inputs tagged in `origin`, **labels written by a person**; must pass `scripts/check_eval_leak.py` with 0 leaks before it is frozen | Chanelle (task E), review Wei-Ling |
| `golden_30.txt` | the 30 golden ids, picked once (stratified by language and clause, seed 42), **never changed** | — |
| `judge_rubric.md` | the grading guideline: five YES/NO criteria and a three-value verdict | Wei-Ling |
| `judge_prompt.txt` | the guideline, copied, as the judge prompt | Wei-Ling |
| `grading_v1.csv` | the 30 golden receipts, a column per grader and for the judge | the two graders |
| `guardrail_cases.jsonl` · `thresholds.yaml` · `runs/` | input-guardrail eval (S6), checked by CI | Wei-Ling |
| `CHANGELOG.md` · `MANIFEST.md` | every look at an eval file, and the hash of each frozen file | everyone |

## The grading guideline (summary; full version `judge_rubric.md`)

A receipt is **sendable** only if all five are YES; **needs edit** if the decision and amount are right but the wording is not; **escalate** if the decision or the amount is wrong, or there is no valid output.

| # | Criterion | Boundary |
|---|---|---|
| 1 | Right decision and rule | right decision, wrong rule = NO |
| 2 | Right amount (to the cent; 0 for decline / need evidence) | €37.46 vs €37.40 = NO |
| 3 | Faithful: no fact that is not in the claim | "wet" when the photo says "dented" = NO |
| 4 | First sentence states the decision; the rule is named and explained | rule code without its meaning = NO |
| 5 | Inside the policy, no blame, no jargon | "we will also refund shipping" = NO |

## Procedure (in this order)

```bash
uv run python -m scripts.run_eval_set --endpoint --file evals/eval_set_v1.csv   # one endpoint session, then undeploy
uv run python -m scripts.judge_kit sheet            # -> grading_v1.csv, 30 golden rows
# two people fill grader_a_verdict and grader_b_verdict separately, without looking at each other's column
uv run python -m scripts.judge_kit judge            # Gemini, temperature 0, prompt = judge_prompt.txt
uv run python -m scripts.judge_kit score            # the two rates below
```

Then read every disagreement, change the guideline **or** the prompt **once**, re-run the judge, and write what changed below. In production a **5 % weekly human sample** keeps checking the judge (`06_07_experiments_operations.md` §3).

## The two agreement rates

| | Value | On | Date | Prototype version |
|---|---|---|---|---|
| **Human–human** (grader A vs grader B, three verdicts) | *to fill* (Cohen's κ *to fill*) | 30 golden rows | *to fill* | model v1 / v2, prompt — |
| **Human–judge** (judge vs the rows where both humans agree) | *to fill* (κ *to fill*) | *n* consensus rows | *to fill* | judge `gemini-3.8-flash` (eu) |
| Both humans: sendable as is | *to fill* / 30 | | | |

- **Graders:** *two team members who did not write the cases (names to fill).*
- **Disagreements and what we changed:** *to fill: one sentence, e.g. "the judge over-accepts receipts with the right decision but a wrong rule; criterion 1 made explicit on <date>".*
- **Known bias:** the judge is a Gemini model, the same family as the photo describer (step 1), not as the drafter (Phi-3, step 3). A description error that Gemini made can look "faithful" to a Gemini judge: criterion 3 is checked against the claim text, not against the photo.
- **Labels stay human:** the judge never writes a label; it only grades the agent's receipt against the human label.
