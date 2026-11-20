# 08 · Launch memo — ParcelCheck (P4) · damaged-parcel refund agent

> **Assembled draft, 16 Nov 2026** — Rania leads (recommendation, risks), Luli (launch plan), Chanelle (evidence); prepared by Wei-Ling. Every number traces to `02_investment_memo.md`, `02_sizing.xlsx`, `evals/report_v0.md`, `spec.md` or `06_07_experiments_operations.md` (numbers checked 16 Nov). The cells marked *to fill* wait for eval v1, the judge rates and the 20 Nov switch test; the format may change after the 20 Nov session (launch memo example).

## Recommendation (line one)
**CONDITIONAL GO.** Ship the **rules-only refund of unused labels first** (no model, €159k a year, the hurdle). Put the **damaged-parcel AI module into 2 weeks of shadow mode** — the agent decides, a person decides, only the person's decision is executed — and move to the A/B by merchant **only if all four conditions below are met**. Today the agent is **safe but not yet useful enough**: 0 wrong automatic refunds, 39 % L4 against a 40 % criterion.

## The four conditions to go from shadow mode to the A/B

| # | Condition | Today | Source |
|---|---|---|---|
| 1 | **Cost of one damaged claim handled by hand ≥ €17.50** (or damaged claims ≥ 19 % of tickets): the flip point of the business case | not measured (as-is guess ≈ €12) → the time study (30 replayed claims) | `02_investment_memo.md` §2 |
| 2 | **L4 ≥ 40 % of decidable claims with 0 wrong automatic refunds and wrong refusals ≤ 2 %**, on eval v1 (100 claims) and in the 2 shadow weeks | 39 % · 0 · 0 on eval v0 (48 claims, 31 photo texts seen in training) · eval v1: *to fill* · model v2 (data v4): *to fill* | `evals/report_v0.md` §2 |
| 3 | **The judge is trustworthy:** human–human and human–judge agreement ≥ 80 % on the 30 golden receipts | *to fill* | `evals/README.md` |
| 4 | **The switch and the prompt rollback are tested** with the two people who can press them | switch tested 7 Nov (failed, fixed, passed); next test 20 Nov incl. the prompt label: *to fill* | `06_07` §4.3 |

## The evidence (Chanelle)

| Question | Answer | Source |
|---|---|---|
| Is it worth it? | Expected value **+€121k** a year vs do-nothing €108k, but **below the hurdle (€159k)** of the rules-only project. No L4 rate alone flips it; the hand cost per claim does (≥ €17.50) | `02_investment_memo.md` |
| Does it work? | 39 % L4 of decidable claims (criterion 40 %), clause 92 %, valid JSON 96 %; a perfect decider reaches 43 % (the €20 limit and "every decline to a person" cap it) | `evals/report_v0.md` |
| Is it safe? | **0** wrong automatic refunds, **0** declines without a person; all 4 model errors stopped before money moved; the injection row (EV09) not paid; the input guardrail catches injection and unsafe messages (eval in CI) | `evals/report_v0.md`, `spec.md` §12 |
| Do users want it? | Merchants wait **3 days** today (a Vinted seller: about a month); a store owner auto-approves under $20 "the time saved is worth more"; **finance disagrees** ("never a refund without approval") — the €20 threshold is the open product decision | `03_user_research.md` #3, #14, `03_product_brief.md` §10 |
| What is still open? | the hand cost per claim (time study); eval v1 and model v2; the judge rates; French claims (a known gap); envelopes and mailers not covered | `03_product_brief.md` §10, `governance.md` S3 |

## Launch plan (Luli)

| Step | What | Gate to the next step | Owner |
|---|---|---|---|
| 0 | Rules-only unused-label refunds | live; leakage on labels ≤ priced | Head of Support |
| 1 | **Shadow mode**, 2 weeks, damaged claims | conditions 1–4 above | PM |
| 2 | **A/B by merchant**, 4 weeks, 622 claims per arm | the decision rule of `06_07` §2: ship if cost per claim −€3, iterate −€1 to −€3, kill < −€1 or any guardrail broken | PM, Head of Support signs |
| 3 | Rollout 10 % → 50 % → 100 % of merchants | the four monitoring layers green for a week at each step (`06_07` §3) | PM |
| 4 | Holdout 5 % of merchants, 6 months | the effect lasts | analyst |

**Rollback at any step:** leakage > €630 per 1,000 damaged claims or wrong refusals > 2 % in a week, or any harmful incident → switch to suggest-only (L1) within 15 minutes (`06_07` §4.3).

## Risks we accept, and the ones we don't
- **Accept:** at most €20 lost per wrong L4 refund (caught by the weekly 5 % sample); a slower answer for the 5 % holdout.
- **Don't accept:** any amount the policy does not give; any decline without a person; a French gap in wrong refusals > 1.5× (the segment drops to L1).

## Who did what

| Member | Main work (final repo commits) |
|---|---|
| Luli | user research and interviews; hand check of the 50 eval labels (found the train/eval leak); prototype step 1; A/B protocol and sample size (`06_07` §1–2); governance S6; launch plan |
| Rania | problem and brief (v1 → v2), user research; prototype step 2; metrics (`05_metrics.md` §1, §2, §4); governance S5; this memo |
| Chanelle | finance interview; prototype step 3; eval-set v1 (100 claims, labels by hand); evaluation plan (`05_metrics.md` §5); eval-data section of the architecture |
| Wei-Ling | sizing and investment memo; architecture; LLMOps pipeline on Vertex AI (data → LoRA → registry → endpoint); Chainlit + Langfuse; input guardrail, CI, prompt versioning; prototype step 4; monitoring and rollback (`06_07` §3–5); spec; governance S7 |

*Each member checks their own line.*
