# 06–07 · Experiments & operations · ParcelCheck (P4)

> Assignment 6 + 7 (due 26 Nov 2026, with `08_launch_memo.md` and the tag `v1.0`). Five sections = the five moves of Sessions 6 + 7: prove · size · watch · contain · own.
> §1–2: Luli (task G, draft assembled 16 Nov — Luli reviews and commits), review Rania · §3–5: Wei-Ling (task H), review Luli. Numbers come from `spec.md` §9–12, `02_sizing.xlsx`, `evals/report_v0.md` and `governance.md`; values marked *planned* are not measured yet.

## 1 · Prove the effect — hypothesis and design

**One sentence per business metric (05_metrics.md §4), each one can be wrong:**
1. *If we let the agent pay damaged-parcel claims of €20 or less automatically (L4) and pre-fill the decision for the rest, for merchants in the treatment arm, then the **refund cost per damaged claim** moves from **€9 to at most €6** by the end of week 4 — without the wrong-refusal rate leaving **≤ 2 %** and without over-refund leakage exceeding **€630 per 1,000** damaged claims.* (The expected effect is ≈ €5.0. A drop of **€3** is the break-even: the module's fixed costs are ≈ €81k a year on ≈ 27,000 damaged claims, `02_investment_memo.md` §2.)
2. *If we do the same, then the **merchant time to resolution** of damaged claims moves from **3 days** to **under 24 hours** for at least 75 % of claims by week 2 — without the human queue missing its 24 h service level.*
3. *If we do the same, then the **wrong-refusal rate stays unchanged** (stop band > 2 % in any week, and French ≤ 1.5× English) through week 4.*

The outcome must exist **with and without the agent**: the L4 share (the primary of §3 of `05_metrics.md`) is 0 in the control arm by construction, so the A/B compares cost per claim, time to resolution and wrong refusals, which exist in both arms.

**Unit of randomisation: the merchant.** A merchant who sees two policies (one claim paid in a minute, the next one in 3 days) would contest the slower one, and merchants learn from their own claims: the effect leaks between claims of the same merchant, not between merchants. Stratified by merchant claim volume.

**Design chain:**

| Step | Design | What it measures | Duration |
|---|---|---|---|
| 1 | **Shadow mode**: the agent decides, a person decides, only the person's decision is executed | the real L4 share and the leakage on real claims, σ and ICC for §2 — no merchant affected | 2 weeks (`spec.md` §11) |
| 2 | **A/B by merchant**: treatment = the agent (L4 ≤ €20, pre-filled L2/L1); control = today's process | the three hypotheses above | 4 weeks (§2) |
| 3 | **Rollout by steps**: 10 % → 50 % → 100 % of merchants, each step guarded by the four layers of §3 | that the effect holds at scale | ≥ 1 week per step |
| 4 | **Holdout**: 5 % of merchants never get L4 for 6 months (disclosed in `governance.md` S6) | whether the effect lasts (drift, novelty) | 6 months |

## 2 · Size it, decide before — sample size and decision rule

**Sample size for the decision metric (cost per damaged claim)** — `spec.md` §11, notebook `evals/sample_size.ipynb`:
`n per arm = 2 (z₀.₉₇₅ + z₀.₈)² σ² / δ² × DE`, with `DE = 1 + (m − 1) · ICC`.

| Input | Value | Where it comes from |
|---|---|---|
| smallest difference the test must see δ | **€1** per claim | the precision we need around the break-even: the decision is €3 (pays the ≈ €81k fixed costs on ≈ 27,000 claims a year) vs €1–3 (iterate) vs < €1 (kill), so the test must tell €1 apart from €0 |
| spread σ | €6 per claim | guess, re-estimated from the shadow-mode weeks |
| claims per merchant m · intra-merchant correlation ICC | 3 · 0.05 | guess, re-estimated in shadow mode |
| two risks | 5 % false win · 20 % missed win | standard |
| **result** | **565 × 1.10 ≈ 622 claims per arm, 1,244 in total** | |
| volume | 2,250 damaged claims a month ≈ 75 a day (`02_sizing.xlsx`) | |
| days for the sample | 1,244 ÷ 75 ≈ **17 days** | |

**Duration: 4 weeks, not 17 days.** The slowest guardrail sets it: wrong refusals are confirmed by contests and re-contacts within 7 days, and leakage is read on the **weekly** 5 % sample — four weekly readings. We look at the decision metric **once**, at the read date.

**The decision rule, written before the first claim:**
- **Ship** (move to the rollout) if cost per damaged claim is down **≥ €3** vs control (the break-even) on the full sample, **and** wrong refusals ≤ 2 % in every weekly reading, **and** leakage ≤ €630 per 1,000, **and** French wrong refusals ≤ 1.5× English.
- **Iterate** if down **€1 to €3**: one more cycle on the misses (same protocol, new read date) — and the time study decides whether a hand-handled claim costs more than the €9 assumed.
- **Kill** if down **less than €1**, or if any guardrail band is broken at any weekly reading.
- **Stop early only on harm** (the threshold in `governance.md` S5–S6), never on a good number.

**Segments pre-registered:** language (FR / EN) · amount band · cover · fragile — reported per segment at the read date, never only the average (Simpson).

**The six questions (slide 13), in words:**
1. *What would convince a sceptical CFO?* A control group of merchants on today's process during the same 4 weeks, not a before/after.
2. *What do we split?* Merchants: the effect would leak between two claims of the same merchant.
3. *Smallest effect that matters?* €3 per claim pays the fixed costs; we size for €1 so the test can tell iterate from kill (halving δ would quadruple n).
4. *Slowest guardrail?* Wrong refusals confirmed by contests and re-contacts (7 days) and the weekly leakage sample → 4 weeks.
5. *Each result → which action?* Ship / iterate / kill above; the harm threshold stops at once; the Head of Support signs.
6. *If we cannot randomise?* Shadow mode first (already planned), then before/after with French claims later than English as a comparison group, stating everything else that changed.

## 3 · Watch the four layers — monitoring and drift

### 3.1 Four layers, four clocks, four owners

| Layer | What we watch (ParcelCheck) | Threshold that pages someone | Clock | Owner | Tool (startup column) |
|---|---|---|---|---|---|
| **Product & guardrails** *(first: the "never" row)* | wrong automatic refunds (L4 amount ≠ policy) · declines sent without a person · input-guardrail blocks by category · wrong-refusal rate · FR vs EN gaps (L4 share, wrong refusals) | **any** wrong automatic refund or decline without a person in a day · wrong refusals > 2 % in a week · FR wrong-refusal rate > 1.5× EN for 2 weeks | daily | Head of Support | Langfuse scores (`guardrail_pass`, `auto_resolved`, `input_guardrail_blocked`) → BigQuery + Looker Studio, by segment |
| **Model quality** | the weekly human sample (5 % of L4 refunds re-decided by a person) → measured leakage · judge vs human agreement on that sample · reviewer agreement 👍/👎 (`reviewer_agrees`) · input-guardrail eval (CI) | judge–human agreement < 80 % · reviewer agreement falling 2 weeks running · guardrail eval below `evals/thresholds.yaml` (CI turns red) | weekly · every PR | the PM | Langfuse (traces, scores, prompt versions) · `scripts/judge_kit.py` · GitHub Actions |
| **Infrastructure** | p95 latency per claim (intake → route) · errors of the Vertex AI endpoint and of Gemini · share of claims handed over because a component was unavailable | p95 > 15 s (`spec.md` §9) for 15 min · errors > 1 % for 10 min · "unavailable" hand-overs > 5 % in an hour | real time | engineer on call (prototype: Wei-Ling) | Google Cloud Monitoring (endpoint) · Langfuse latency · Slack webhook for paging |
| **Business** | refund cost per damaged case (processing + leakage) · over-refund € per 1,000 damaged claims (from the weekly sample) · merchant time to resolution · merchant re-contact within 7 days | leakage > **€630 per 1,000** damaged claims in a week (`spec.md` §12) · cost per case not falling by month 2 · re-contact up vs control | weekly / monthly | Head of Support + CFO | weekly query on the claims table → shared sheet / Looker Studio |

A dashboard nobody is paged by is a screensaver: each row has a threshold, a clock and a name. Notebook that computes the four rows from the Langfuse traces: `evals/monitoring.ipynb` (task J).

### 3.2 Drift — the four kinds, for our agent

| Kind | What it looks like for ParcelCheck | Signal that catches it | What we do |
|---|---|---|---|
| **Model drift** *(the first one we expect — it already happened once)* | the provider changes or retires a model: Gemini 2.5 Flash was retired on Vertex AI on 20 Oct 2026 and returned 404 on our first photo test (`evals/CHANGELOG.md`) | Gemini errors and "unavailable" hand-overs jump; the input-guardrail eval moves without a commit | pin every model id (`prompts/input_guardrail.yaml`, `GEMINI_MODEL`); re-run the guardrail eval and test A/B on any version change before L4 is re-enabled (`spec.md` §12); prompt-drift test: `run_guardrail_eval --model <new>` |
| **Data drift** | new kinds of claims: envelopes and mailers (the classifier only knows boxes), new item categories, more French messages | share of `need_evidence` +50 % week on week; item mix PSI > 0.2 on `item_category`; FR share shift (`spec.md` §12) | report by segment; add the new cases to the eval-set and the training data, retrain |
| **Concept drift** | the refund policy changes (v1.1 → v1.2: a new cap, a new rule): a decision that was right last month is wrong now | every policy change is a release: labels regenerated from `policy.py`, eval-set re-labelled | the policy version is in every trace and receipt; L4 stays off until test A/B pass on the new labels |
| **Knowledge drift** | the rule text quoted in receipts and in the prompt ages (an old clause wording) | receipts citing a rule text that differs from `policy.py` (judge criterion 4) | the rule text comes from `policy.py` (single source of truth), not from the prompt |

**Where it runs.** Today: the Chainlit app and the four steps on a laptop (`localhost:8000`, demo in class); the fine-tuned model on a **Vertex AI endpoint** (europe-west2, deployed only for an eval or the demo, ≈ $1/h); traces in **Langfuse Cloud, EU region**; Gemini at the `eu` location. Pilot target: the same Docker image on **Google Cloud Run, europe-west2** (same GCP project and region as the endpoint, data stays in the EU; rollback = previous image). The €0 path for the course: laptop + Langfuse Cloud Hobby + endpoint only on demo day.

## 4 · Contain the incident — trace, incident classes, rollback

### 4.1 One trace per claim (OpenTelemetry, already running)
The Langfuse v3 SDK emits **OpenTelemetry** spans (`telemetry.sdk.name: opentelemetry` in every trace), so any OTel backend can read them. One claim = one trace `refund-claim`:

| Span (nested under `refund-claim`) | Attributes we log |
|---|---|
| `refund-claim` (root) | case id, `autonomy_enabled`, tags = trust level and route, input claim, output (route, action, trust level) |
| `input-guardrail` (generation) | model (`gemini-3.5-flash-lite`), **linked prompt version** (Langfuse `input-guardrail` v1 = semver 1.1.0), `prompt_source`, category, reason |
| route → rule → `decide` (generation) | endpoint id and model version (registry version), prompt and generation parameters, raw model output, latency |
| check (guardrail) | recomputed amount, guardrail reasons, final trust level |
| scores | `guardrail_pass`, `auto_resolved`, `input_guardrail_blocked`, `reviewer_agrees` (👍/👎) |

Kept 30 days on the Langfuse Hobby plan (prototype); 90 days in production (`governance.md` §3: needs a paid plan or self-hosting).

### 4.2 Four incident classes

| Class | Example on ParcelCheck | How we see it | Action |
|---|---|---|---|
| **Caught** | the model writes €37.46 instead of €37.40, or invalid JSON (EV41, EV05 in `report_v0.md`): the guardrail recomputes or hands over | `check` span has guardrail reasons; route L1/L2 | count weekly; a `spec.md` line if it repeats |
| **Sent wrong** | an L4 refund ≤ €20 paid on a misread photo (bounded: at most €20) | the weekly 5 % sample re-decides it differently; merchant re-contact within 7 days | correct the payment, receipt apology, add the case to the eval-set |
| **Harmful** | an amount the policy does not give is paid; a decline sent without a person; an injection gets a refund through; a receipt shows another merchant's data | wrong automatic refund count > 0; decline without a `human_decision`; a complaint; a DPO alert | **rollback now** (§4.3), incident report, DPO if personal data |
| **Outage** | the endpoint is undeployed or down; Gemini returns errors | `decide` errors, "unavailable" hand-overs, endpoint error rate | automatic: every claim goes to the human queue (the input guardrail and the endpoint call **fail closed**, `spec.md` §6) |

The harm threshold of `governance.md` is the line between "sent wrong" and "harmful".

### 4.3 The rollback plan — six fields

| Field | ParcelCheck |
|---|---|
| **1 · Trigger** | leakage > €630 per 1,000 damaged claims or wrong refusals > 2 % in the weekly reading · any "harmful" incident · the guardrail eval below its thresholds · a new model or prompt version that has not passed the evals |
| **2 · Who decides** | Head of Support; at night the engineer on call (prototype: Wei-Ling), who then informs the Head of Support. Finance (CFO) can request it |
| **3 · The action** | three positions of the switch: **ON** (L4 under €20 as designed) → **suggest-only, L1** (`AUTONOMY_ENABLED=false`: the agent suggests, nothing is paid or sent without a person) → **humans-only** (the human queue, what an outage does by itself). Prompt problem: move the Langfuse `production` label back to the previous version. Model problem: redeploy the previous Model Registry version (`DATA_MODEL_CARD.md` §2), switch at L1 meanwhile |
| **4 · Time to execute** | switch: from the next claim, no deploy, one person — today `switch off` in the reviewer console or `AUTONOMY_ENABLED=false`; in the target API `POST /admin/autonomy` — under 15 minutes from a phone · prompt label: under a minute (the app re-reads it every 60 s) · model redeploy: 15–30 minutes, with the switch at L1 meanwhile |
| **5 · What people see** | merchants: "A person will check this claim (within 24 h)"; reviewers: the queue grows, every claim arrives pre-filled; the trace keeps logging |
| **6 · Last tested** | **7 Nov 2026** (Wei-Ling): the switch test **failed** first (12 claims still L4: the variable was never read), was fixed and re-run: 0 L4 of 48 (`evals/report_v0.md` §4). **Next test, planned: 20 Nov 2026**, before the pitch, with the two people who can press it — including the prompt-label rollback, not tested yet |

Rolling back is not failing; not being able to is.

## 5 · Own the system — five decisions, five names

| Decision | Owner (role · prototype name) | Written where |
|---|---|---|
| Run an experiment on real merchants | Head of Support signs the protocol; the DPO reads it | §1–2 · `governance.md` S6 |
| Read the weekly numbers and act | the PM, every Monday, the four layers of §3 | §3 |
| Press the switch | Head of Support · engineer on call at night (prototype: Wei-Ling) | §4.3 · `governance.md` S7 |
| Approve a release (new prompt, model, policy) | the PM, with the eval-set and the guardrail eval re-run attached (CI green) | `evals/README.md` · `.github/workflows/` |
| Keep the trace, answer a merchant or a regulator | engineering keeps the traces (Langfuse); Legal answers; receipts are statements the company is held to (Moffatt v. Air Canada, 2024) | `governance.md` S1 Q5, S7 |

EU AI Act art. 50 (from 2 Aug 2026): every receipt says it was prepared by an AI system and how to reach a person — already in the app. Art. 26 (deployer monitors, keeps logs, assigns human oversight) is the standard we copy, even though ParcelCheck is not high-risk.
