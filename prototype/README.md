# /prototype: ParcelCheck in four steps

```
claim (+ photo) ─▶ [1 route] ─▶ [2 rule] ─▶ [3 decide] ─▶ [4 check] ─▶ L4: refund paid (≤ €20, every check passes)
                      │ out of scope  │ switch off              │ any guardrail reason ─▶ ⊘ a person (L2 approves · L1 decides)
                      └───────────────┴─────────────────────────┘
⏻ AUTONOMY_ENABLED=false (or "switch off" in the app): every claim goes to a person. Owner: Head of Support.
```

| Step | File | Rung | Pattern | Commit | Owner |
|---|---|---|---|---|---|
| 1 Router | `steps/step1_route.py` | 3 (Gemini photo facts) + 1 (scope keywords) | routing | `step-1-router` | Luli |
| 2 Routing rule | `steps/step2_rule.py` | 1 | routing on a rule | `step-2-rule` | Rania |
| 3 Decide | `steps/step3_decide.py` | 3→4 (Phi-3 + LoRA, Vertex AI endpoint) | prompt chaining | `step-3-decide` | Chanelle |
| 4 Policy check | `steps/step4_check.py` | 1 | verifier | `step-4-policy` | Wei-Ling |
| Eval | `../scripts/run_eval_set.py` | — | — | `eval-v0` | — |

The steps call the shared code in `../src/agent/` (policy, guardrail, model calls), so the app, the eval
and the training pipeline use the same rules.

```bash
uv run python -m prototype.pipeline                                       # the four demo claims, no cloud
uv run python -m scripts.run_eval_set [--endpoint]                        # the number (evals/report_v0.md)
GCP_ENDPOINT_ID= uv run chainlit run prototype/chainlit_app/main.py -w    # the app, http://localhost:8000
```

Demo data (`demo_cases.jsonl`) is never in the eval set (`../evals/eval_set_v0.csv`).
