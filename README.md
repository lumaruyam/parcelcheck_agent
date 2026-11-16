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
parcel_refund_agent/
├── 01_problem_statement.md      # Product A1: problem, personas, hypotheses
├── 02_investment_memo.md        # Product A2: go / no-go decision
├── 02_sizing.xlsx               # Product A2: sizing model
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

> **Note:** the four-step prototype (`prototype/pipeline.py`, `prototype/steps/`) and the later product files (`03_*` to `08_*`, `spec.md`) are still on the team draft repo / branch `p4/wei-ling/step-4-check`. `prototype/chainlit_app/main.py` imports `prototype.pipeline`, so the app needs that merge before it starts from `main`.

---

## Getting started

### Prerequisites

- Python **3.11** (see `.python-version`) and [`uv`](https://docs.astral.sh/uv/)
- For cloud features: the [`gcloud` CLI](https://cloud.google.com/sdk/docs/install), access to the class GCP project, and a Langfuse Cloud (EU) project

### 1. Install

```bash
git clone git@github.com:lumaruyam/parcel_refund_agent.git
```

```bash
cd parcel_refund_agent && uv sync
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

In the app: **📦 File a claim** (guided questions + photo), **✨ Try an example** (4 demo claims), 👍 / 👎 to record reviewer agreement, type `switch off` / `switch on` to test the override switch, `person` to reach a human.

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

Then deploy the registered model to an endpoint and put its id in `GCP_ENDPOINT_ID`. Data versions and rebuild commands: [`data/README.md`](data/README.md).

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
