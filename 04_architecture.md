# 04 — Architecture · ParcelCheck (P4)

> v1.1, 6 Nov 2026 · Session 4 deliverable: the diagram, the component table, the patterns, the trust levels, the checkpoints ⊘ and the switch ⏻.
> **Part A** decodes the system in the Session 4 vocabulary (Anthropic, *Building effective agents*, Dec 2024). **Part B** is the infrastructure on the course's GCP setup: region **europe-west2** (`GCP_REGION`), GPU **NVIDIA T4** (course quota).
> Same decisions as `spec.md`. If the two disagree, `spec.md` wins and this file is fixed.

---

# Part A — Decode the architecture

## 1. The pipeline in one picture

**In:** a damaged-parcel claim (label fields, merchant message, 1–3 photos). **Out:** an executed refund ≤ €20 with its receipt, or a prepared decision in a person's queue.

```
 Intake ──► Classify photo ─┐
 (rules)    (YOLO, pretrained)├─► Cross-check ──► Decide clause ──► Guardrail ──► Route ──► Act ──────────► Log
            Describe photo ─┘    (rules)         + receipt         (rules,       (rules)   L4: pay ≤ €20   (rules)
            (Gemini, pretrained)                 (Phi-3)           recompute €)            L2/L1: queue
   L4        no autonomy          L4             L2 → L4 only       L4             L4        L4 / person      L4
                                                 through ⊘5
             ⊘ no detection ──────────────────────────────────────────────────────► L1 (abstention)
                                  ⊘ disagree ─────────────────────────────────────► L1 (abstention)
                                                                    ⊘ € mismatch ──► L1 (abstention)
                                                                                 ⊘ €20–100, any decline ──► L2 (approval)
                                                                                 ⊘ > €100, need_evidence ─► L1 (abstention)
 ⏻ AUTONOMY_ENABLED=false → the router never returns L4 or L2: every claim is L1, the agent only suggests, nothing is paid or sent.
```

The detailed infrastructure diagram is in §8.

## 2. Component table

| # | Component | Pattern | Rung (S4 archetype) | Trust level | Checkpoint |
|---|---|---|---|---|---|
| 0 | Intake + idempotency on `claim_id` | rule-based | 1 rules | L4 | — (duplicate → stored result, never pay twice) |
| 1 | Classify photo: damaged / normal / none | parallelization (sectioning), branch 1 | 3 pretrained (YOLOv11n) | no autonomy: input to step 3 | — |
| 2 | Describe photo: packaging, item visible, item state, usable | parallelization (sectioning), branch 2 | 3 pretrained (Gemini 2.5 Flash) | no autonomy: facts only | — |
| 3 | Cross-check the two vision outputs | rule-based merge (gate) | 1 rules | L4 | ⊘ abstention: `disagree` or `no_detection` → L1 |
| 4 | Decide clause + amount + receipt | prompt chaining, grounded on the policy text and steps 2–3 | 3 pretrained, prompt-only in v0 → fine-tuned (LoRA) only if the eval says so (§5.3) | L2 by default; L4 only through steps 5–6 | — |
| 5 | Guardrail: recompute the amount from `policy.py`, check coherence | rule-based (a verifier, not an evaluator-optimizer loop) | 1 rules | L4 | ⊘ abstention: amount ≠ policy, clause impossible for the label → L1 |
| 6 | Route by money and by evidence | routing on a rule | 1 rules | L4 | ⊘ approval: €20–100 and every decline → L2 · ⊘ abstention: > €100, `need_evidence`, out of scope → L1 |
| 7 | Act: pay ≤ €20 to the ledger (stub) + send the receipt, or enqueue | rule-based | 1 rules | L4 ≤ €20 · person above | — |
| 8 | Review: approve / edit / decide → the final decision becomes a label | person | — | person only | the reviewer is the checkpoint |
| 9 | Log: Langfuse trace with model versions + stored receipt | rule-based | 1 rules | L4 | weekly ⊘ sample: a person re-decides 5% of L4 |

**Whole system:** rung 4, hybrid — each part on its own rung, wired together by a spec.

## 3. Workflow or agent?

**A workflow, not an agent.** The path is drawn in advance in `spec.md` §3. The model never chooses its next step or a tool.

| | ParcelCheck |
|---|---|
| Who decides the path | We do, in the spec: 0 → 1‖2 → 3 → 4 → 5 → 6 → 7. No loop |
| Cost per claim | Predictable: 1 YOLO call (CPU), 1 Gemini call, 1 Phi-3 call, at most 1 transport retry |
| When it fails | At a known step, with a known fallback (`spec.md` §6), e.g. "step 5: amount €45.00 ≠ policy €31.50" |
| Can we explain it | Yes: the receipt names the clause, the photo evidence and the amount; the trace names the step |
| Trust level it carries | L4 / L2 / L1 per step, chosen by us, never by the model's confidence |
| Tools | No free tool use. The orchestrator calls a fixed list: `classify_photo`, `describe_photo`, `decide`, `policy.decide` (recompute), `ledger.write_refund`, `queue.enqueue`, `notify_merchant` (stub) |

**Patterns we do not use, and why:**
- **Agent (ReAct loop):** money is paid at the end of the path. A loop that "decides each step itself" with a refund tool is the Chevrolet failure (AI Incident Database #622, 2023).
- **Evaluator–optimizer:** the guardrail does not send the draft back to the model for a retry. On failure it hands over to a person. No loop, so no runaway cost.
- **Orchestrator–workers, multi-agent:** one claim is one decision; there is nothing to decompose. A multi-agent setup would cost ~15× the tokens (Anthropic, June 2025) for a €4.90–€20 refund.

## 4. Human checkpoints ⊘ and the override switch ⏻

A checkpoint is a place in the flow where a named person approves, corrects or takes over. It is set by the design, not by the model's confidence.

| ⊘ | Where | Kind | Who | Service level |
|---|---|---|---|---|
| 1 | Refund €20.01–€100 | approval: approve / edit | refund agent (reviewer queue) | within 24 h |
| 2 | Every decline (R4 late claim, R5 fragile without option) | approval: a wrong refusal loses a merchant silently | refund agent | within 24 h |
| 3 | Refund > €100 (premium cover) | abstention: the agent only suggests, a person decides | senior refund agent / team lead | within 24 h |
| 4 | `need_evidence` (R6), unusable photo, item not shown | abstention | refund agent: asks the merchant for a photo of the item | within 24 h |
| 5 | Vision disagreement, no detection, guardrail failure (amount ≠ policy, impossible clause, injection) | abstention | refund agent; both amounts shown, the policy amount pre-filled | within 24 h |
| 6 | Out of scope (lost parcel, not delivered, other language) | abstention | refund agent, standard queue | within 24 h |
| 7 | Weekly sample: 5% of L4 refunds re-decided | audit sample (L3-style) | Support QA | every Monday, on the previous week |

**⏻ The override switch.**
- **What it does:** one action, `AUTONOMY_ENABLED=false` (env variable or `POST /admin/autonomy`), drops the whole system to **L1**. The agent still reads the claim and shows its suggestion, but nothing is paid and no receipt is sent without a person.
- **Effect time:** the next claim. No deploy.
- **Owner:** Head of Support. Finance can request it. On-call: [name].
- **When:** the rollback trigger in `spec.md` §12 (leakage > €630 per 1,000 claims or wrong refusals > 2% in a week), a model version change not yet re-validated, or any incident.
- **Tested before launch:** the eval is re-run with the switch off, and must show 0 L4, 0 ledger writes and 0 receipts sent (`spec.md` §10).

**The Chevrolet answer, for our system.** The bot stated a price with no rule in front of it, and the only switch was "unplug the bot". Here a rung-1 rule recomputes every amount before it is paid (step 5), the human checkpoints are fixed by the money band (step 6), and the switch is one flag with an owner.

## 5. The four decisions (Session 4 workshop)

### 5.1 The pipeline
Drawn in §1. In: a claim; out: a refund ≤ €20 or a prepared decision. One rung per step (§2).

### 5.2 The routing rule
- **Human-only, by name:** every decline · every refund > €20 · premium refunds > €100 · `need_evidence` · lost / not-delivered parcels · claims with vision disagreement or no detection · any guardrail failure.
- **The threshold:** L4 only if *all* hold — guardrail pass, amount ≤ **€20**, cross-check `agree`, photo usable. The €20 comes from the P4 proposal and the cost of an error (at most €20 lost, caught by the weekly sample).
- **The cost of a wrong route, both ways:**

| Error | What happens | Cost | Which is expensive |
|---|---|---|---|
| Routed to L4 when a person was needed | over-refund paid silently | up to €20 per claim (L4 cap), more on a systematic error | **the expensive one when it is systematic** (e.g. a cap misread on every claim): hence the guardrail and the € rollback |
| Routed to a person when L4 was fine | a reviewer spends ≈ 3 min (guess), the merchant waits up to 24 h | ≈ €2 of reviewer time (guess) | cheap: we accept it |
| A decline executed without a person | wrong refusal; the merchant re-contacts or leaves | ≈ 2 tickets + churn risk (Moffatt v. Air Canada, 2024) | expensive and reputational: declines are never L4 |

### 5.3 The decider
- **May read:** the label fields of *this* claim, the redacted merchant message, the Gemini description, the policy text v1.1.
- **May not read:** other merchants' claims, the label photo (personal data), payment data, anything outside the prompt.
- **Must show as evidence:** the clause id and its text, the photo description quoted, the label facts used, the amount. This is the receipt (`spec.md` §4).
- **Nothing found / low confidence / API down:** Gemini down → "No photo assessment available" → R6 → L1. Phi-3 down → L1, with the `policy.py` result shown as a "rule suggestion" (never executed). Invalid JSON → one transport retry → L1. The model never composes an answer outside the policy.
- **Rung choice for v0 (the one-day prototype rule):** v0 runs the **prompt-only base model** (rung 3 with a good prompt). The LoRA fine-tune is the climb to the rung above. It is built for the Agentic Workflows course, and it is **kept in the product only if it beats the prompt-only model by ≥ 30 points** on clause-and-amount (`02_investment_memo.md` §5).

### 5.4 The policy check, the cases, the number
- **Three things the model is never trusted with:** (1) the amount paid — always recomputed by `policy.py`; (2) a decline — always a person; (3) any promise outside the policy, and any instruction found in the merchant message (injection).
- **Five cases, one per type** (from `evals/eval_set_v0.csv`): easy EV02 (R1 €16.90, L4) · hard EV20 (vision disagreement → L1) · out of scope EV15 (lost parcel) · other segment EV13 (FR, premium, cap €512.40, L1) · the trap EV09 (injection "refund €500" → only €4.90 may ever be paid).
- **The number we report on 6 Nov, against the criterion:** the share of decidable claims routed L4 with the right amount, and the count of wrong L4 refunds (must be 0) — `evals/report_v0.md`.

## 6. One metric, one main risk

- **Metric:** share of decidable damaged claims resolved at L4 with **zero** wrong automatic refunds (target ≥ 40%, `spec.md` §10).
- **Main risk:** a systematic over-refund, such as a premium cap applied to standard cover on every claim, paid silently at L4. Second risk: a missed `need_evidence` (item not visible) refunded as R1.

## 7. Demo data vs evaluation data, and where the eval-set comes from

| | Demo set | Evaluation set |
|---|---|---|
| What | 4 claims that show the feature at its best (README demo script) | `evals/eval_set_v0.csv` (20 → 50 → 200) + test A (300), A-adv (40), B (100) |
| Who picks | We do | Drawn to look like real traffic: easy, hard, out of scope, FR/EN, every amount band, the trap oversampled |
| Where | `prototype/demo_cases.jsonl` — **no row shared with the eval set** | `evals/`, `data/test_*.jsonl`, frozen and hashed in `evals/MANIFEST.md` |
| Rule | We look at them while we build | Never tune while looking. A row we tuned on becomes demo data, and we say so in `evals/report_v0.md` |

**Origin of the eval-set (as `evals/README_eval_set.md` asks).** No real customer data. Every row carries `origin`:
- `invented` — written by hand (EV15, EV16) or from templates;
- `synthetic-template`, `synthetic-gemini`, `bitext-derived` — test A and the training set;
- `roboflow-<dataset>` — test B photos, real-public, CC BY 4.0, hand-labelled by two of us with κ;
- `kled` — test C, only if licensed.

The labels of `eval_set_v0.csv` were drafted with `policy.py` and **must be checked by hand by someone who did not write the case**, before any run (initials and date in `notes`). The cases are not generated with the prompt the decider uses.

---
