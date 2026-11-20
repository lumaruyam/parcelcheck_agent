# Grading guideline ("rubric") — is the decision receipt sendable as is? · ParcelCheck (P4)

> Assignment 5 §5. Written **before** anyone grades (13 Nov 2026). The judge prompt (`evals/judge_prompt.txt`) is this guideline, copied.
> What is graded: the **decision receipt** the agent writes for one claim (the model's JSON: `decision`, `clause`, `amount_eur`, `receipt`), read against the claim and its label (`expected_output_or_action` in the eval-set).
> The app adds the AI disclosure and "type person to talk to a human" under every receipt (`prototype/chainlit_app/main.py`), so those lines are not graded here.

## Five criteria (YES / NO each)

| # | Criterion | YES means | Boundary examples |
|---|---|---|---|
| 1 | **Right decision and rule** | `decision` (refund / decline / need_evidence) and `clause` (R1–R6) are the ones in the label | right decision, wrong rule (R1 instead of R5) = **NO** |
| 2 | **Right amount** | refund: `amount_eur` equals the label's amount to the cent; decline / need_evidence: amount is 0 and no amount is promised in the text | €37.46 instead of €37.40 = **NO** (the guardrail recomputes it, but the receipt as written is wrong) |
| 3 | **Faithful** | every fact in the receipt (photo description, days since delivery, cover, declared value, options) is in the claim; nothing is added | "the box was wet" when the photo text says "dented" = **NO**; leaving out a fact = YES |
| 4 | **Cites the rule clearly** | the first sentence states the decision; the receipt names the rule and gives its reason in plain words | "Refund approved: €16.90. Rule R1: …" = YES; the rule code without its meaning = **NO** |
| 5 | **Inside the policy, merchant-ready** | no promise outside the policy (extra refund, a deadline, "we will reship"), no blame on the merchant or the courier, no internal jargon (L4, guardrail, JSON) | "we will also refund your shipping" = **NO**; an English receipt to a French merchant = YES in v0 (all receipts are English today), reported as a segment gap |

## Verdict (three values, as in Assignment 5)

| Verdict | When | What happens in the product |
|---|---|---|
| **sendable** | all five YES | can be sent unedited (L4, or one click at L2) |
| **needs edit** | 1 and 2 YES, at least one of 3–5 NO | the decision is right, a person fixes the wording |
| **escalate** | 1 or 2 NO, or no valid output | the decision itself is wrong: a person decides (L1) |

## How it is used (procedure, `evals/README.md`)
1. Two team members grade the same **30 golden cases** independently (`evals/grading_v1.csv`, columns `grader_a_*`, `grader_b_*`): human–human agreement.
2. The judge grades the same 30 (`scripts/run_judge.py`): human–judge agreement.
3. Read every disagreement; fix this guideline or the prompt **once**; write both rates and the change in `evals/README.md`.
4. In production: a 5 % weekly human sample keeps checking the judge (`06_07_experiments_operations.md` §3).
