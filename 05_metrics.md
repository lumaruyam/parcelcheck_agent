# 05 · Metrics — ParcelCheck (P4) · damaged-parcel refund agent

> **Assembled draft, 16 Nov 2026** — §1, §2, §4: Rania (task F) · §3: Luli · §5: Chanelle. Prepared by Wei-Ling from the three drafts in `drafts/`; each owner reviews and commits their sections in the final repo with their own account (A5: at least two members commit).
> Session 5 deliverable. Five sections = the five moves of the session. **Every number traces to `02_sizing.xlsx` (base case, via `02_investment_memo.md`) or `evals/report_v0.md`** — no new number appears here. Where a number is derived, the arithmetic is written next to it.

## 1 · Place the number — the stack for our agent
One metric per level. "Produced by" = which evaluation type.

| Level | Question | Our metric | Value today (or "not yet") | Produced by | Owner | Clock |
|---|---|---|---|---|---|---|
| 5 Business | does it move the P&L? | refund cost per damaged claim (handling + leakage) | baseline **€9** per ticket (02_sizing, base); not yet with the agent | finance data, monthly | CFO | months |
| 4 Product | does the merchant get the job done? | merchant time to resolution · share of damaged claims resolved at L4 in production | baseline **3 days** (P4 proposal, measured); not yet | A/B by merchant, then production, weekly | PM | weeks |
| 3 Guardrails & responsible AI | does it stay inside the lines — for everyone? | wrong automatic refunds · declines sent without a person · by segment (FR / EN, amount band) | **0** wrong automatic refunds and **0** declines without a person on 48 claims; EV09 injection not paid (report_v0 §2) · by segment: not yet (eval v1) | eval-set + adversarial rows, each release; then the weekly 5 % sample | PM + DPO | days |
| 2 AI system | does the workflow complete the task? | **L4 share of decidable claims (R1–R3) with the right amount** | **39 %** (11 claims) vs criterion 40 % (report_v0 §2) · routing agrees with the label 46/48 (96 %) | eval-set + two graders | AI engineer (Wei-Ling) | hours |
| 1 Model | is the component right? | clause accuracy · valid JSON | **92 %** (44/48) · **96 %** (46/48) (report_v0 §2) | offline eval-set, every change | ML engineer | seconds |

A better number at level 1 is a hypothesis about level 5, not a result: the arrows are written in §4.

## 2 · Decide when to stop — the stop criterion
*"We stop improving the decision model's **clause accuracy at 92 %** because **the L4 share stops responding** — a perfect decider (the policy stub) reaches only **43 %** of decidable claims, because the €20 limit and 'every decline goes to a person' send the rest to L2 (report_v0 §0) — so the next model points can add at most **4 points of L4**, and each would cost **a retrain and a full re-evaluation (€4,000 per model change, 02_sizing base)**."*

- Component metric and value: clause accuracy 92 % (valid JSON 96 %).
- The level-above metric that stops responding: the L4 share (39 % today, ceiling 43 %).
- Cost of the next point: one retrain + re-evaluation (€4,000 per model change, 02_sizing); a full eval session on the endpoint.
- **Where the next sprint goes instead:** the time study. The decision flips on the **cost of one damaged claim ≥ €17.50** (base €9), not on the model (`02_investment_memo.md` §2).
- **Floors, not stops (any miss blocks the release):** **0 wrong automatic refunds** and **0 declines sent without a person**. Below 99 % valid JSON is not a floor: an invalid output is caught by the guardrail and goes to a person.

## 3 · Choose what to protect — the hierarchy, by segment
| Kind | Metric | Numerator / denominator | Level | Lag | Source & owner |
|---|---|---|---|---|---|
| **Primary (1)** | L4 claims paid with the right amount and not contested within 7 days | L4 claims whose amount = policy and with no contest or re-contact within 7 days / decidable damaged claims (R1–R3) | 4 product | 7 days | claims table + weekly 5 % sample · PM |
| Guardrail | wrong automatic refunds | L4 claims whose amount ≠ policy / L4 claims — **must be 0** (floor) | 3 | 1 week (sample) | weekly 5 % sample · Head of Support |
| Guardrail | wrong-refusal rate | refund-eligible claims declined or sent back for evidence / refund-eligible claims — **≤ 2 %** | 3–4 | 1–4 weeks | reviewer decisions + contests · Head of Support |
| Guardrail | human-queue time | claims decided by a person later than 24 h / claims sent to a person — **0 %** target | 4 | 1 day | queue timestamps · Head of Support |
| Counter-metric | over-refund leakage | Σ (paid − policy amount) on L4 claims / 1,000 damaged claims — priced **€315**, rollback **€630** | 5 | 1 week | weekly 5 % sample · CFO |
| Counter-metric | churn of merchants who received a decline | merchants with a declined claim who stop shipping within 90 days / merchants with a declined claim | 5 | 90 days | CRM · Head of Support |

- **Segments reported:** language (FR / EN) · amount band (≤ €20 / €20–100 / > €100) · cover (standard / premium) · fragile (yes / no); merchant volume tier for the A/B strata.
- **Fairness metric:** **equal error rates** — the wrong-refusal rate per segment, French vs English first (French messages are a known gap of the S3 audit; 17 eval v0 rows tagged `fr` had English text).
- **Harm threshold (copied in `governance.md` S5):** French wrong refusals > 1.5× English for two consecutive weeks, or any segment > 2 % in a week → that segment drops to L1 until explained. Owner: Head of Support, reviewed with the DPO monthly.
- **Where the thresholds come from (decisions, not measurements):** ≤ 2 % wrong refusals and the €630 rollback — `02_investment_memo.md` §3; 24 h human service level — `governance.md` S4; €315 priced leakage — 300 L4 × 3 % × €35 (`02_sizing.xlsx` Inputs rows 26, 30); 7-day contest window, 1.5× FR/EN ratio and 90-day churn window — team decisions written here, to revisit after shadow mode.
- **How it could be gamed → the repair:** the primary rises if more claims are paid without checks or if the €20 limit is raised quietly → leakage is measured by people on a random sample, and the limit lives in `policy.py`, changed only by a release with the eval re-run. "Not contested within 7 days" can be gamed by making contests hard → the receipt always says how to reach a person (EU AI Act art. 50), and contest volume is itself watched.

## 4 · Derive the business metrics — three, with expected effects (the oral)

| Business metric | Baseline (`02_sizing.xlsx`) | Expected effect (from `evals/report_v0.md` × the cost line) | Lag | Read date | It is a hypothesis about… |
|---|---|---|---|---|---|
| **Refund cost per damaged claim** (handling + leakage) | **€9** per ticket (base) | **€9 → ≈ €5.0** — 39 % L4 of decidable × 75 % decidable = **29 %** of damaged claims at L4 (≈ €0 handling; AI €0.02 × 1.2 retries); **46 %** decided by a person with a pre-filled decision (−40 % handling time, `02_sizing.xlsx` Inputs row 67, base — a guess to test with the time study); **25 %** not decidable, unchanged; + leakage 29 % × 3 % × €35 = **€0.31** | 1 month | end of month 2 of the A/B | L4 share holds on real claims (39 % was measured on 48 synthetic claims) **and** the pre-filled decision saves time on L2/L1 |
| **Merchant time to resolution** | **3 days** (P4 proposal, measured) | **3 days → under 1 minute for the 29 % at L4**; the rest within the 24 h human service level (`governance.md` S4) | 1 week | week 2 of the A/B | the human queue keeps its 24 h service level when it receives pre-filled claims |
| **Wrong-refusal rate** (refund-eligible claims declined or sent back for evidence) | today's human process (not in the sizing: read in shadow mode weeks 1–2) | **unchanged — stated as a non-effect**, stop band **> 2 % in any week** (`02_investment_memo.md` §3); over-refund leakage stays within the **€315 per 1,000** priced (300 L4 × 3 % × €35), rollback at **€630** | 1–4 weeks (re-contact, contest) | weekly, decision at week 4 | the guardrail and "every decline goes to a person" protect merchants as well as money |

**The tree (component → product → business), with the claimed effect sizes:**

```
MODEL      clause accuracy 92 % · valid JSON 96 %
   │  "+ model points add at most 4 pts of L4" (ceiling 43 %, stub)
   ▼
AI SYSTEM  L4 share of decidable claims 39 % · 0 wrong automatic refunds
   │  "× 75 % decidable → 29 % of damaged claims at L4"
   ▼
PRODUCT    29 % resolved in < 1 min · the rest ≤ 24 h (was 3 days)
   │  "29 % at ≈ €0 + 46 % at −40 % time + 25 % unchanged + €0.31 leakage"
   ▼
BUSINESS   refund cost per damaged claim €9 → ≈ €5.0 · wrong refusals unchanged (≤ 2 %) · leakage ≤ €315 / 1,000
```

Read with the investment memo: even at this effect the AI module does not clear the hurdle (expected value €121k vs €159k for the rules-only project); the decision flips if a damaged claim costs ≥ €17.50 by hand. The three metrics are the promises the A/B tests (`06_07_experiments_operations.md` §1–2).

## 5 · Make the judge trustworthy — the evaluation plan
- **Eval-set v1:** `evals/eval_set_v1.csv`, **100 claims** (200 in production), stratified by language (49 FR · 49 EN · 2 other), amount band, cover and fragile; 24 inputs are descriptions of real public photos (Gemini), 66 synthetic claims and 10 guardrail / service cases, all tagged in `origin`; **labels written by a person** — *to confirm: Chanelle reviews every row (initials and date in `notes`) before this line is true*; **0 leaks** with the training data (`scripts/check_eval_leak.py`). A **golden set of 30** (`evals/golden_30.txt`) never changes.
- **Grading guideline:** `evals/judge_rubric.md` — five YES/NO criteria (right decision and rule, right amount, faithful, rule cited clearly, inside the policy) and three verdicts (sendable / needs edit / escalate), written before anyone graded. Two graders on the same 30 rows: agreement = **not measured yet** (billing blocked, see `evals/README.md`).
- **Judge:** Gemini 3.8 Flash (`eu`, temperature 0), prompt `evals/judge_prompt.txt`; human–judge agreement on the rows where both graders agree = **not measured yet: Gemini and the endpoint return 403 (billing) since 17 Nov, re-checked 20 Nov; procedure ready in `evals/README.md`**; known bias: the judge is the same model family as the photo describer (step 1), not as the decision model (Phi-3); to be re-aligned after reading the disagreements, once the rate is measured (`evals/README.md`).
- **Cadence:** eval-set + judge on every change of prompt, model or policy (CI checks the input guardrail on every PR); a **5 % weekly human sample** of L4 refunds in production.
- *Optional, not graded — red rows:* the guardrail eval (`evals/guardrail_cases.jsonl`, 45 cases, prompt injection, abuse, personal data, out of scope) already runs in CI with thresholds.
