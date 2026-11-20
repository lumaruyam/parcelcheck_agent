# Launch memo — ParcelCheck (P4), damaged-parcel refund agent — 26 Nov 2026

> One page, in the six parts of the S8 template. Every number traces to `02_investment_memo.md`, `02_sizing.xlsx`, `evals/report_v0.md`, `05_metrics.md` or `06_07_experiments_operations.md`. Eval v1 and the judge rates are not measured yet (billing blocked, §2). Draft restructured 20 Nov (Wei-Ling) from the 16 Nov version (Rania, Luli, Chanelle).

## 1 · Decision
**Conditional go** — step 0 now: the **rules-only refund of unused labels** (no model, €159k a year). The damaged-parcel AI module goes to **step 1, shadow mode for 2 weeks** (the agent decides, a person decides, only the person's decision is executed), from **Mon 1 Feb 2027**, and to the A/B by merchant **only if the four gate conditions of §3 are met**. Today the agent is safe but not yet useful enough: 0 wrong automatic refunds, 39 % decided alone against a 40 % criterion. The next decision is read on **Fri 12 Feb 2027** by the Head of Support and the PM; the A/B, if it starts, runs 15 Feb – 12 Mar and is read once, on **Mon 15 Mar 2027**. January is for the gate work: the time study, eval v1 and the judge rates.

**Budget we ask for:** **€97.5k a year**, the fixed costs of `02_sizing.xlsx`. It pays for the 5 % weekly human sample (€13.5k), the integration (€30k, amortised), evaluation and hand-labelling (€20k) plus re-evaluation at each model change (€12k), and monitoring including a 24/7 T4 endpoint (€22k).

## 2 · Evidence
- **Eval:** eval v1 (100 cases, two graders on 30, judge agreement human–human / human–judge): **not measured yet** — Gemini and the endpoint return 403 (billing) since 17 Nov, re-checked 20 Nov; one endpoint session and one hour of grading when billing is back. Criterion: **"≥ 40 % of decidable claims decided alone (L4), with 0 wrong automatic refunds"**. Today, on eval v0 (48 claims): **39 % L4, 0 wrong automatic refunds**, right clause 92 %, valid JSON 96 %. Caveat: 31 of those photo texts were seen in training, which is why eval v1 is new and leak-checked.
- **Guardrails:** **0** wrong automatic refunds and **0** declines without a person out of 48; the injection row was not paid. Input guardrail v1.1.0 on 45 labelled cases: injection recall 1.00, unsafe recall 1.00, benign false positives 0.00, checked in CI on every PR that touches the prompt.
- **What the A/B will prove:** refund cost per damaged claim from **€9** to **≤ €6** (≈ €5.0 expected); **622 claims per arm** (σ €6, smallest gain that pays €3); **4 weeks**, because the slowest guardrail sets it: wrong refusals are confirmed by contests within 7 days, and leakage is read on the weekly 5 % sample.
- **Sizing:** base €117k a year vs hurdle **€159k** (rules-only, the next-best project); EV **€121k**; do-nothing trajectory **€108k**. The decision flips if one damaged claim costs **≥ €17.50** by hand (as-is guess ≈ €12).

## 3 · Rollout steps
| Step | Scope | Duration | Gate (metric · threshold · read date) | Signs the next step |
|---|---|---|---|---|
| 0 | rules-only unused-label refunds live · AI module in staging | now | criterion met on eval v1 · no red row · switch tested | PM |
| 1 | **shadow mode**, all damaged claims, nothing executed by the agent | 2 weeks · 1–12 Feb 2027 | the four gate conditions below · read on 12 Feb 2027 | Head of Support |
| 2 | **A/B by merchant**, 50 % of merchants | 4 weeks · 15 Feb – 12 Mar 2027 · 622 claims per arm | ship if cost per claim down ≥ €3 · iterate €1–3 · kill < €1 or any guardrail broken · read once, on 15 Mar 2027 | PM + Head of Support |
| 3 | rollout 10 % → 50 % → 100 % of merchants, **5 % holdout** | ≥ 1 week per step · holdout 6 months | the four monitoring layers green for a week at each step · monthly drift review | PM |

**Gate from shadow to the A/B (all four):**
1. One damaged claim costs **≥ €17.50** by hand (or damaged claims ≥ 19 % of tickets): the time study, 3 interviews + 30 replayed claims. Today: not measured.
2. **L4 ≥ 40 %** of decidable claims with **0 wrong automatic refunds** and **wrong refusals ≤ 2 %**, on eval v1 and in the 2 shadow weeks. Today: 39 % · 0 · 0 on eval v0.
3. **The judge is trustworthy:** human–human and human–judge agreement **≥ 80 %** on the 30 golden receipts. Today: not measured (billing blocked); graders Luli and Rania, procedure in `evals/README.md`.
4. **The switch and the prompt rollback are tested** with the two people who can press them. Today: see §4.

## 4 · Rollback & the switch
Trigger: leakage **> €630 per 1,000** damaged claims or wrong refusals **> 2 %** in any weekly reading, any harmful incident, or the guardrail eval below its thresholds · Who decides: **Head of Support** (at night: the engineer on call, prototype Wei-Ling, who informs the Head of Support) · Action: **suggest-only, L1** (`switch off` in the reviewer console, or `AUTONOMY_ENABLED=false`: the agent suggests, a person decides every claim) → humans-only; a prompt problem: move the Langfuse `production` label back · Time to execute: **< 15 min** from a phone, no deploy (prompt label < 1 min) · What people see: merchants "A person will check this claim (within 24 h)"; reviewers a longer queue, every claim pre-filled.
**Last tested: 20 Nov 2026**, scripted re-run, offline (Wei-Ling): switch off → **0 claims decided alone of 48** (eval v0) and **0 of 90** (eval v1 draft); control with the switch on → 12 of 48 (`evals/runs/20261120_switch-test_*`). First test 7 Nov: failed (12 still L4), fixed, passed. **Drill with the two people who press it, prompt-label rollback included: planned Tue 24 Nov 2026, in class (Rania as Head of Support, Wei-Ling on call).**

## 5 · Owners — and who signs
| Decision | Owner | Written where |
|---|---|---|
| run an experiment on real merchants | Head of Support signs; the DPO reads | `06_07` §1–§2 · `governance.md` S6 |
| read the weekly numbers and act | the PM, every Monday | `06_07` §3 |
| press the switch | Head of Support; at night the engineer on call | `06_07` §4 · `governance.md` S7 |
| approve a release (prompt, model, policy) | the PM, with the eval set and the guardrail eval re-run (CI green) | `evals/README.md` |
| keep the trace, answer a merchant or a regulator | engineering keeps the traces (Langfuse); Legal answers | `governance.md` S1, S7 |

**This launch is signed by the Head of Support and the PM.**

## 6 · What we do not know yet
- **Is the quality as good in French?** Wrong refusals in French must stay within 1.5× English; not measured on real claims. Next experiment: report the language segment in the 2 shadow weeks; if the gap is larger, French claims drop to L1.
- **Will finance accept €20 refunds without approval?** A store owner auto-approves under $20, finance says "never without approval". Next experiment: show the CFO the leakage measured on real claims in shadow mode before the A/B.
- **The number we could not measure: what one damaged claim really costs by hand.** It decides the launch (flip at €17.50, guess ≈ €12). How we will: the time study, 3 interviews + 30 claims replayed with a stopwatch, approval wait included.
