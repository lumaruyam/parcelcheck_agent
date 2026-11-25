# ParcelCheck — damaged-parcel refunds decided in a minute

ParcelCheck is an AI agent for a shipping-label and returns platform. A merchant reports a parcel that arrived damaged and uploads a photo. The agent describes the damage, applies the refund policy and writes a decision receipt. Refunds of €20 or less are paid automatically when every check passes; everything else is prepared for a person to approve or decide.

**Courses:** Agentic Workflows (MSA-DAT07-03) · Data & AI Product: From Diagnosis to Delivery (MSA-DAT07-04) — Albert School, cohort M2-INTER-2
**Starting point:** P4 — refund and cancellation agent for an e-commerce logistics SaaS, narrowed to damaged-parcel claims (switched from P7 with the professor's approval).

---

## Team

| Name | GitHub | Main contributions |
|---|---|---|
| **Luli** | [@lumaruyam](https://github.com/lumaruyam) | S2 data: refund policy, synthetic claims v1/v4, data transformation, eval leak check · prototype step 1 (router) |
| **Rania** | [@raniamehria](https://github.com/raniamehria) | S3 training: LoRA fine-tuning, inference, evaluation, Kubeflow pipeline, output guardrail · prototype step 2 (routing rule) |
| **Chanelle** | [@csanchez-cyber](https://github.com/csanchez-cyber) | S4 serving: custom handler, model registration, Gemini photo describer and photo eval · prototype step 3 (decide) |
| **Wei-Ling** | [@whung99](https://github.com/whung99) | S1 GCP setup · S5 Chainlit app, Langfuse tracing, monitoring · S6 input guardrail, versioned prompts, CI · prototype step 4 (policy check) |

Every member commits with their own Git account (the individual oral question is about a commit you signed).

---

## The problem in short

- The platform handles **25,000 tickets a month**; 30% are refunds, and about **2,250 a month** are damaged-parcel claims that need a photo check.
- Each claim takes 12–17 minutes by hand (photo, label system, policy arithmetic), merchants wait **≈ 3 days**, and a €5 refund costs more to process than it is worth.
- **Goal:** within 6 months, ≥ 40% of decidable damaged claims refunded automatically in under a minute, with **zero wrong automatic refunds**.
- **The one thing it must never do:** pay an amount the policy does not give for the facts on the label. The amount is always recomputed by rules, never taken from the model.

Details: [`01_problem_statement.md`](01_problem_statement.md), [`02_investment_memo.md`](02_investment_memo.md), [`02_sizing.xlsx`](02_sizing.xlsx), [`governance.md`](governance.md).

---

## AI Product deliverables

One numbered file per session, as in the course repo template. Owners follow the rounds of the team PR guide; the full checklist with every requirement is in [`DELIVERABLES_CHECKLIST.md`](DELIVERABLES_CHECKLIST.md).

Status on 25 Nov 2026: ✅ on `main` · ⬜ to do

| File | Session · due | Owner(s) | Status |
|---|---|---|---|
| [`01_problem_statement.md`](01_problem_statement.md) | S1–S2 · A1 | Chanelle | ✅ |
| [`02_sizing.xlsx`](02_sizing.xlsx), [`02_investment_memo.md`](02_investment_memo.md) | S2 · A2 | Chanelle | ✅ |
| [`03_product_brief.md`](03_product_brief.md) | S3 · A3, final 26 Nov | Rania, Chanelle | ✅ v2 |
| [`03_ai_lean_canvas.md`](03_ai_lean_canvas.md) | S3 · A3 | Luli, Wei-Ling | ✅ 14 blocks |
| [`03_user_research.md`](03_user_research.md) | S3 · A3 | all four | ✅ |
| [`03_prototype_link.md`](03_prototype_link.md) | S3 · A3 | Chanelle, Luli, Wei-Ling | ✅ |
| [`04_architecture.md`](04_architecture.md) | S4 · A4 | Wei-Ling, Rania | ✅ v1.3 |
| [`prototype/`](prototype/) four steps | S4 · A4 | one step each | ✅ |
| [`evals/eval_set_v0.csv`](evals/eval_set_v0.csv) (50) · [`evals/report_v0.md`](evals/report_v0.md) | S4 · A4 | Chanelle · Wei-Ling | ✅ |
| [`spec.md`](spec.md) | S3 → final 26 Nov | Rania, Wei-Ling | ✅ v3 |
| [`05_metrics.md`](05_metrics.md) | S5 · A5, 22 Nov | Rania §1, 2, 4 · Luli §3 · Chanelle §5 | ✅ · judge rate not measured yet (billing blocked) |
| [`evals/eval_set_v1.csv`](evals/eval_set_v1.csv) (100) | S5 · A5, 22 Nov | Chanelle, Wei-Ling (hand check) | ✅ |
| [`evals/judge_rubric.md`](evals/judge_rubric.md), [`judge_prompt.txt`](evals/judge_prompt.txt), [`evals/README.md`](evals/README.md) (two agreement rates) | S5 · A5, 22 Nov | Chanelle, Wei-Ling | ✅ · rates not measured yet (billing blocked) |
| [`06_07_experiments_operations.md`](06_07_experiments_operations.md) | S6–S7 · 23 Nov | Luli §1–2 · Wei-Ling §3–5 | ✅ |
| [`08_launch_memo.md`](08_launch_memo.md) | S8 · 26 Nov | Rania · Luli · Chanelle | ✅ six S8 parts |
| [`governance.md`](governance.md), one line per session | S1 → S8 | all four | ✅ S1–S8 |
| tag `v1.0` | 26 Nov | — | ⬜ |

**Pitch:** Friday 27 Nov, 8 min + 3 min of questions, everyone speaks; the demo shows a normal claim, a refused claim and the score. Slides and the demo video are not in Git.

---

## Architecture

```
            merchant (Chainlit app)
                     │ claim form + photo
                     ▼
 ┌───────────────────────────────────────────┐
 │ 0. Input guardrail  (Gemini Flash-Lite)    │── not "safe" ──────────────┐
 │    safe / injection / abusive /            │                            │
 │    out_of_scope / personal_data            │                            │
 └───────────────────────────────────────────┘                            │
                     ▼                                                     │
 ┌───────────────────────────────────────────┐                            │
 │ 1. Photo description  (Gemini 3.8 Flash)   │  facts only, no decision   │
 └───────────────────────────────────────────┘                            │
                     ▼                                                     │
 ┌───────────────────────────────────────────┐                            │
 │ 2. Decide  (Phi-3-mini + LoRA, Vertex AI   │  JSON: clause, decision,   │
 │    endpoint — or offline policy stub)      │  amount, receipt           │
 └───────────────────────────────────────────┘                            │
                     ▼                                                     │
 ┌───────────────────────────────────────────┐                            │
 │ 3. Output guardrail  (rules, policy.py)    │── any reason ──────────────┤
 │    valid JSON? known clause? amount =      │                            │
 │    policy amount? window? coherent photo?  │                            ▼
 └───────────────────────────────────────────┘                   ⊘ human queue (24 h)
                     ▼                                             L2: person approves €20–100, every decline
       L4: refund ≤ €20 executed                                   L1: person decides > €100, unclear photo
                                                                       
 ⏻ AUTONOMY_ENABLED=false (or "switch off" in the app) → every claim goes to a person
 📈 Every claim = one Langfuse trace (span, generation, scores)
```

### Refund policy (`src/agent/policy.py` — single source of truth)

| Clause | Rule | Outcome |
|---|---|---|
| R1 | Content damaged, standard cover | item value up to €25 + label fee |
| R2 | Content damaged, premium cover | item value up to €500 + label fee |
| R3 | Packaging damaged, content intact | label fee only |
| R4 | Claim filed > 7 days after delivery | declined |
| R5 | Fragile item without fragile option or padding | declined |
| R6 | No visible damage or unusable photo | more evidence, a person decides |

### Trust levels

| Level | When | Who acts |
|---|---|---|
| **L4** | refund ≤ €20 and every check passes | the agent alone; 5% weekly human sample |
| **L2** | refund €20–100, and every decline | the agent drafts, a person approves |
| **L1** | refund > €100, unclear photo, any incoherence | a person decides |

### Training & serving (GCP, `europe-west2`)

```
data/cases_v4.jsonl ─▶ GCS ─▶ Vertex AI Pipeline (Kubeflow)
                              ├─ data transformation (chat format, 85/15 split, seed 42)
                              ├─ fine-tuning: Phi-3-mini-4k-instruct, 4-bit QLoRA, NVIDIA T4
                              ├─ inference on the held-out test split (greedy)
                              └─ evaluation: right clause, right amount (to the cent), right trust level
                         ─▶ Model Registry (src/handler.py + HF pre-built container) ─▶ Vertex AI endpoint
```

### Tech stack

Python 3.11 · `uv` · Vertex AI (Pipelines, Model Registry, Endpoints, Gemini) · Kubeflow Pipelines · Hugging Face `transformers` / `peft` / `trl` · Chainlit · Langfuse Cloud (EU) · pydantic · pytest · ruff · mypy · GitHub Actions

---

## Repository structure

```
parcelcheck_agent/
├── 01_problem_statement.md      # Product A1: problem, personas, hypotheses
├── 02_investment_memo.md        # Product A2: go / no-go decision
├── 02_sizing.xlsx               # Product A2: sizing model
├── 03_product_brief.md          # Product A3: brief v2 (what users changed)
├── 03_ai_lean_canvas.md         # Product A3: AI lean canvas, 14 blocks
├── 03_user_research.md          # Product A3: interviews, usability test, what we heard
├── 03_prototype_link.md         # Product A3: clickable prototype + prompt
├── 04_architecture.md           # Product A4: architecture, trust levels, costs
├── 05_metrics.md                # Product A5: metrics and evaluation plan
├── 06_07_experiments_operations.md # Product A6–7: A/B protocol and operations
├── 08_launch_memo.md            # Product S8: launch memo
├── spec.md                      # agent spec: every eval miss becomes a line
├── DATA_MODEL_CARD.md           # data and model card
├── DELIVERABLES_CHECKLIST.md    # course deliverables, owners and status
├── governance.md                # living governance file (AI Act, GDPR, trust levels…)
├── chainlit.md                  # welcome screen of the app
├── src/
│   ├── agent/
│   │   ├── policy.py            # refund rules R1–R6, trust levels (single source of truth)
│   │   ├── agent.py             # end-to-end: claim → model → guardrail → route; override switch
│   │   ├── guardrail.py         # output guardrail: recomputes every amount
│   │   ├── input_guardrail.py   # input guardrail (Gemini classifier, fail closed)
│   │   ├── vision.py            # Gemini photo description
│   │   ├── generate_cases.py    # synthetic claims labelled by the policy
│   │   ├── templates_v4.py      # EN/FR claim templates (data v4)
│   │   ├── make_sft.py          # claims → SFT chat format
│   │   └── evaluate.py          # before/after evaluation
│   ├── pipeline_components/     # Kubeflow components: transform, fine-tune, inference, evaluation
│   ├── pipelines/               # Vertex AI training pipeline definition
│   ├── evaluation/              # guardrail eval harness, run records, monitoring layers
│   ├── handler.py               # custom inference handler for the Vertex AI endpoint
│   └── constants.py             # every setting, read from .env
├── prototype/
│   ├── pipeline.py              # the four steps chained: route → rule → decide → check
│   ├── steps/                   # step1_route, step2_rule, step3_decide, step4_check
│   ├── chainlit_app/main.py     # the merchant / reviewer console
│   └── demo_cases.jsonl         # 4 demo claims (never in train or eval sets)
├── prompts/input_guardrail.yaml # versioned prompt (semver), pushed to Langfuse
├── data/                        # synthetic claims and photo descriptions (see data/README.md)
├── evals/                       # photo test sets & reports, guardrail cases, thresholds, runs, monitoring notebook
├── scripts/                     # pipeline runner, model registration, evals, CI checks, utilities
├── tests/                       # pytest suite (no cloud calls)
├── infra/langfuse/README.md     # Langfuse Cloud setup and prompt management
├── docs/                        # break-the-build report, screenshots
└── .github/workflows/           # CI (lint, types, tests) and guardrail eval check
```

> **Status:** the four-step prototype (`prototype/pipeline.py`, `prototype/steps/`) and every product file of the course are on `main`. What is left before the `v1.0` tag is in [`DELIVERABLES_CHECKLIST.md`](DELIVERABLES_CHECKLIST.md).

---

## Getting started

### Prerequisites

- Python **3.11** (see `.python-version`) and [`uv`](https://docs.astral.sh/uv/)
- For cloud features: the [`gcloud` CLI](https://cloud.google.com/sdk/docs/install), access to the class GCP project, and a Langfuse Cloud (EU) project

### 1. Install

```bash
git clone https://github.com/lumaruyam/parcelcheck_agent.git
```

```bash
cd parcelcheck_agent && uv sync
```

### 2. Configure

```bash
cp .env.example .env
```

Fill in `.env` (never commit it):

| Variable | Used for |
|---|---|
| `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_BUCKET_NAME` | Vertex AI and GCS |
| `GCP_PROJECT_NUMBER`, `GCP_ENDPOINT_ID` | the deployed Phi-3 endpoint (leave `GCP_ENDPOINT_ID` empty to use the offline stub) |
| `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST` | tracing and prompt management |
| `AUTONOMY_ENABLED` | override switch: `false` sends every claim to a person |
| `GEMINI_MODEL`, `GEMINI_LOCATION` | photo description |
| `INPUT_GUARDRAIL`, `PROMPT_SOURCE`, `PROMPT_LABEL` | input guardrail (`false` to skip it without a Google login) |

Log in to Google Cloud (needed for Gemini and the endpoint):

```bash
gcloud auth login && gcloud auth application-default login
```

```bash
uv run python -m scripts.validate_gcp_setup
```

### 3. Run the agent

Offline, no cloud (policy stub, free):

```bash
uv run python -m src.agent.agent
```

The Chainlit app at http://localhost:8000 — offline stub:

```bash
GCP_ENDPOINT_ID= INPUT_GUARDRAIL=false uv run chainlit run prototype/chainlit_app/main.py -w
```

With the fine-tuned model (endpoint deployed and `GCP_ENDPOINT_ID` set):

```bash
uv run chainlit run prototype/chainlit_app/main.py -w
```

In the app:

- **Type what happened** ("the box arrived crushed and the mug is broken"): the input guardrail reads it first. An unsafe or off-topic message goes to a person; a damage description starts a claim with your words already filled in.
- **📦 File a claim**: guided one-tap questions, then a photo or your typed description.
- **✨ Try an example**: 4 demo claims. **📜 My claims** (or type `history`): your last 10 claims with their result, trust level and Langfuse trace.
- 👍 / 👎 records reviewer agreement; `switch off` / `switch on` tests the override switch; `person` reaches a human.

Describe a single photo with Gemini:

```bash
uv run python -m src.agent.vision path/to/photo.jpg --json
```

### 4. Train and deploy the model (GCP)

```bash
uv run python -m src.agent.generate_cases --n 1500 --seed 42 --out data/cases.jsonl
```

```bash
gcloud storage cp data/cases_v4.jsonl gs://$GCP_BUCKET_NAME/data/
```

```bash
uv run python -m scripts.pipeline_runner --data-file cases_v4.jsonl --epochs 1 --max-test-samples 50
```

```bash
uv run python -m scripts.register_model_with_custom_handler --model-uri gs://<bucket>/pipeline_root/<...>/fine-tune_<id>/model
```

Then deploy the registered model to an endpoint and put its id in `GCP_ENDPOINT_ID` (command in the next section). Data versions and rebuild commands: [`data/README.md`](data/README.md).

### 5. For graders: run it with the same model

Three levels, from nothing to the full system. Every level runs the same app and the same refund policy (`src/agent/policy.py`); only the parts that need the cloud change.

| Level | What you need | What runs |
|---|---|---|
| **0 · Offline** | `uv` only | the whole chat, history, policy and trust levels; decisions come from the policy stub instead of Phi-3; no photo, no guardrail |
| **1 · Gemini** | a Google login with access to the class project (`gcloud auth application-default login`) | + photo description and the input guardrail |
| **2 · Fine-tuned model** | + the endpoint deployed (below) | + decisions from our fine-tuned Phi-3 (Vertex AI Model Registry `parcelcheck-phi-3-mini`, version 2) |

Level 0, in three commands:

```bash
git clone https://github.com/lumaruyam/parcelcheck_agent.git && cd parcelcheck_agent && uv sync
```

```bash
cp .env.example .env
```

```bash
GCP_ENDPOINT_ID= INPUT_GUARDRAIL=false uv run chainlit run prototype/chainlit_app/main.py
```

Level 2: the model is stored in the Model Registry, so it does not need retraining. Deploying it takes about 15–20 minutes and costs about $1 per hour (n1-standard-8 + 1 × T4), so we undeploy it after each demo. Tell us when you want to test it and we deploy it for that slot, or deploy it yourself. You need an endpoint first: ours is in the team's `.env`, or make your own and put its id in `GCP_ENDPOINT_ID`:

```bash
gcloud ai endpoints create --region=europe-west2 --display-name=parcelcheck-grader
```

Then deploy version 2 of the model to it:

```bash
gcloud ai endpoints deploy-model $GCP_ENDPOINT_ID --region=europe-west2 \
  --model=1379229584905469952@2 --display-name=parcelcheck-phi3-v2 \
  --machine-type=n1-standard-8 --accelerator=type=nvidia-tesla-t4,count=1 \
  --min-replica-count=1 --max-replica-count=1 --traffic-split=0=100
```

```bash
uv run chainlit run prototype/chainlit_app/main.py
```

The first answer is slow (model warm-up). When you have finished, undeploy (the id is printed by `gcloud ai endpoints describe $GCP_ENDPOINT_ID --region=europe-west2`):

```bash
gcloud ai endpoints undeploy-model $GCP_ENDPOINT_ID --region=europe-west2 --deployed-model-id=<DEPLOYED_MODEL_ID>
```

CI proves level 0 on every pull request: `tests/test_app_smoke.py` starts the app with no endpoint and no keys and decides a claim end to end.

---

## Evaluation

| What | How | Result so far |
|---|---|---|
| Decision model | pipeline evaluation component: right clause, right amount, right trust level | see pipeline run outputs |
| Photo reading (Gemini, prompt v1) | `uv run python -m scripts.run_photo_eval` on 100 real Roboflow photos | intact read as intact 28/28; damaged read as damaged 24/37 usable; **0** photos wrongly read as content damage ([`evals/photo_report_v1.md`](evals/photo_report_v1.md)) |
| Input guardrail v1.1.0 | `uv run python -m scripts.run_guardrail_eval` on 45 labelled cases | injection recall 1.00, unsafe recall 1.00, benign false-positive rate 0.00, category accuracy 1.00 |
| Eval-set leakage | `uv run python -m scripts.check_eval_leak --eval evals/<file>.csv` | fails on any exact or near duplicate of training text |

Guardrail thresholds live in [`evals/thresholds.yaml`](evals/thresholds.yaml) (injection recall ≥ 0.95, unsafe recall ≥ 0.90, benign FP ≤ 0.10, category accuracy ≥ 0.85, 0 errors). The "break the build" experiment is in [`docs/break_the_build.md`](docs/break_the_build.md).

---

## Observability & prompt management

- **Langfuse Cloud (EU):** one trace per claim — span `refund-claim`, generation `decide`, scores `guardrail_pass`, `auto_resolved`, `reviewer_agrees`. Setup: [`infra/langfuse/README.md`](infra/langfuse/README.md).
- **Monitoring:** `src/evaluation/monitoring.py` and `evals/monitoring.ipynb` turn a week of traces into alert layers and per-segment metrics.
- **Prompts:** Git (`prompts/*.yaml`, semver) is the source of truth; Langfuse serves the `production` label. Rollback = move the label, no redeploy.

```bash
uv run python -m scripts.push_prompt_to_langfuse
```

---

## Tests & CI

```bash
uv run pytest -q
```

```bash
uv run ruff check . && uv run mypy
```

- **`ci.yml`** — on every PR and push to `main`: ruff, mypy (strict on the Session 6 code), pytest. No cloud calls.
- **`guardrail_eval.yml`** — on PRs touching the prompt, guardrail or eval: the class GCP project does not allow service accounts, so the eval runs on a laptop and its results are committed in `evals/runs/`. CI checks the committed run matches the prompt and cases (sha256), recomputes the metrics and fails on a threshold breach.

---

## Governance & data

- **EU AI Act:** limited risk (art. 50 transparency): every receipt says it was prepared by an AI and how to reach a person.
- **Data:** synthetic claims labelled by our policy, public Roboflow parcel photos (CC BY 4.0), no real customer data in Git. Photos stay out of Git (`evals/photos/` is ignored).
- **Human in the loop:** every decline and every refund > €20 goes to a person; the `AUTONOMY_ENABLED` kill switch is owned by the Head of Support.

Full answers: [`governance.md`](governance.md).

---

## Team rules

- Work on a branch named `s<session>/<name>/<topic>`, open a PR to `main`, merge after review and green CI.
- Commit with your own Git account; never commit `.env`, keys or real photos.
- Tag the final version `v1.0` before the first oral of the cohort. No commits after the first oral starts.
