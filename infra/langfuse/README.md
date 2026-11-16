# Langfuse (Session 5): Langfuse Cloud (EU), Hobby plan

Langfuse records one **trace** per claim handled by the Chainlit app. We use **Langfuse Cloud, EU region**
(data stays in the EU, `governance.md`), free Hobby plan: 50k units a month, 30 days of data, 2 users.
Nothing to install or keep running, and the whole team can see the same traces.

## 1. Project and keys (once)

1. https://cloud.langfuse.com (EU; `us.cloud.langfuse.com` is a different account) › sign up › organisation
   `parcelcheck` › project `parcelcheck`.
2. **Settings › API keys › Create**. The snippet must show `https://cloud.langfuse.com`; a key made in another
   instance (e.g. a local Docker one at `localhost:3000`) gives `401 Invalid credentials`.
3. **Settings › Members**: invite one teammate (Hobby allows 2 users), so the project does not depend on one login.

## 2. Connect the app

Put the keys in `.env` (never committed, never pasted in chat or a PR):

```
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Check the connection (prints `auth_check: True`, a test trace appears under **Tracing**):

```bash
uv run python -c "from dotenv import load_dotenv; load_dotenv(); from langfuse import Langfuse; print(Langfuse().auth_check())"
```

Self-hosting is still possible (`git clone https://github.com/langfuse/langfuse && docker compose up -d`, then
`LANGFUSE_HOST=http://localhost:3000`), but it only runs on one laptop: we moved to Cloud on 12 Nov.

## 3. Run the app and send claims

```bash
# demo without the cloud (policy stub, free):
GCP_ENDPOINT_ID= uv run chainlit run prototype/chainlit_app/main.py -w     # http://localhost:8000
# with the fine-tuned model: deploy the endpoint first (04_architecture.md §10), then
uv run chainlit run prototype/chainlit_app/main.py -w
```

Click **✨ Try an example** (DEMO-01 … DEMO-04), then 👍 / 👎 under each decision. Type `switch off` to test the override switch,
`switch on` to restore it. If the endpoint is undeployed, claims go to a person: they never crash.

## What one trace contains

| Level | Input | Output |
|---|---|---|
| span `refund-claim` | the raw claim | route, action, trust level, guardrail reasons; tags = trust level and route |
| generation `decide` | the templated prompt + generation parameters | raw model text, latency, endpoint id |
| score `guardrail_pass` | — | 1 if no guardrail reason, else 0 |
| score `auto_resolved` | — | 1 if paid or sent without a person (L4) |
| score `reviewer_agrees` | the reviewer's 👍 / 👎 | 1 / 0: the ground truth we collect for free (Session 5) |

## Monitoring we read in Langfuse (`05_metrics.md`)

- Share of claims auto-resolved (`auto_resolved`), share stopped by the guardrail (`guardrail_pass` = 0).
- Reviewer agreement (`reviewer_agrees`): if it drops, the model or the data drifted.
- Latency of `decide` (p95), by model version.
- Optional, LLM-as-a-judge (needs an LLM key in Langfuse): "the receipt cites the clause and the amount";
  "the receipt says the decision was prepared by an AI and how to reach a person".


## Prompt management (Session 6.3)

Git is the source of truth: `prompts/input_guardrail.yaml` with a semver (MAJOR = output contract,
MINOR = behaviour, PATCH = wording). Langfuse serves the version labelled `production` to the app.

```bash
uv run python -m scripts.push_prompt_to_langfuse                  # new version, labels v<semver> + production
uv run python -m scripts.push_prompt_to_langfuse --no-production  # candidate only (label v<semver>)
```

- The app asks Langfuse for `production` on every claim (cached 60 s) and rebuilds the guardrail only when the
  version changes. Each `input-guardrail` generation is linked to the prompt version (Langfuse › Prompts › Metrics).
- **Rollback:** Langfuse › Prompts › `input-guardrail` › move the `production` label to the previous version. No
  code change, no redeploy; the app picks it up within a minute.
- If Langfuse is down or the prompt was never pushed, the app uses the Git file (`PROMPT_SOURCE=file` forces it).
- The eval harness and CI always test the **Git** file, so a PR is tested before its prompt is pushed.
