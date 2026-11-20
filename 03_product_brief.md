# 03 — Product brief · ParcelCheck, damaged-parcel refund agent · v1

> Session 3. One page. Built from `01_problem_statement.md` and `02_investment_memo.md`.
> v1: 6 Nov 2026. v2 after the three interviews and the usability test: §9–10 stay empty until then (no invented research).

**Team:** Luli, Rania, Wei-Ling, Chanelle · **Starting point:** P4 · **Version:** v1 — 06/11/2026

## 1. Problem, user, do-nothing *(from 01)*

- **Problem in one sentence (with a number):** 7,500 refund tickets a month are handled by hand, 2,250 of them damaged-parcel claims that need a photo check. That is ≈ €810k a year of handling, and merchants wait 3 days for refunds that are often under €20.
- **User (persona):** Inès, refund agent (reviewer queue). Goal: 30 tickets a day at QA ≥ 90. Pain: photo + label system + cap arithmetic on every claim. **Customer:** Thomas, a merchant shipping 400 parcels a month, who wants the money back before the end customer complains.
- **Do-nothing baseline:** about 4% a year of process improvement (≈ €108k); the 3-day wait stays. The real competitor is the rules-only unused-label auto-refund (€159k base).

## 2. The process — as-is and to-be (damaged-parcel claim)

| # | Step | Who today | Minutes | Error rate | Cost of an error | Automate / augment / keep human (test it fails) | Trust level | Minutes after | Metric for this step |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Read the claim, identify the type | Agent | 2 (guess) | 3% (guess) | A lost parcel handled as damaged | **Automate**: structured form + tracking status (rules) | L4 | 0 | Share routed out of scope correctly |
| 2 | Open the photo, judge the damage | Agent | 3 (guess) | 10% (guess) | Wrong clause → wrong amount | **Augment**: YOLO + Gemini describe; fails test 5 (*no need to explain the decision*), so the description is quoted in the receipt | no autonomy (input) | 0 (+1 when the reviewer looks) | Gemini item-state agreement vs hand label (test B) |
| 3 | Look up the label: cover, value, fragile option, dates | Agent | 3 (guess) | 2% (guess) | Wrong cap | **Automate**: label-system API (rules) | L4 | 0 | Field completeness |
| 4 | Apply the policy, compute the amount, write the reply | Agent | 5 (guess) | 5% (guess) | Over-refund ≤ €25/€500 + fee, or a wrong refusal | **Automate under a threshold**: Phi-3 picks the clause and writes the receipt; **rules recompute the amount** | L4 ≤ €20 · L2 €20–100 · L1 > €100 | 0 at L4 | Clause & amount correct; wrong L4 = 0 |
| 5 | Approve > €20 / every decline | Team lead | 2 + wait | — | Same as 4 | **Keep human**: fails test 6 (*tolerance for error*) above €20 | L2 / L1 | 3 (L2 approve) · 8 (L1 decide) | Reviewer agreement with the agent; time per review |
| 6 | Execute the refund, send the message | Agent | 2 (guess) | 1% (guess) | Paid twice | **Automate**: refund ledger + idempotency on claim id | L4 | 0 | Duplicate payments = 0 |

All minutes and error rates are **guesses**, to be checked by the time study and the interviews. As-is ≈ 17 min (≈ €12); after: 0 min at L4, ≈ 3 min at L2, ≈ 8 min at L1.

- **Where the pain sits (the two steps):** step 2 (photo judgement) and step 4 (cap arithmetic and policy across three tools).
- **The way back to a person (designed first):** every step can route to the reviewer queue. Any failed check, any vision disagreement, any `need_evidence` and any decline goes to a person. A kill switch ⏻ (`AUTONOMY_ENABLED`, owner Head of Support) drops everything to L1 from the next claim: the agent only suggests, nothing is paid without a person. Checkpoints ⊘ and their owners: `governance.md` Session 4.
- **Where the governance line sits:** at money. L4 only ≤ €20 and only when the rules agree with the model; refusals always go through a person (reputational risk, owner Head of Support).

*Trust levels: L1 suggests · L2 drafts, a person approves · L3 acts on a scope, a person samples · L4 acts alone under a threshold.*

## 3. Features — RICE and MoSCoW

| Feature | Reach / month (from 02_sizing.xlsx) | Impact | Confidence | Effort (person-weeks) | RICE | MoSCoW |
|---|---|---|---|---|---|---|
| F5 Unused-label auto-refund rules (category 2) | 5,250 | 2 | 80% | 2 | 4,200 | SHOULD — ships first, as its own release (the hurdle) |
| F2 Decision receipt (merchant message = audit log) | 2,250 | 1 | 80% | 1 | 1,800 | **MUST** |
| F3 Reviewer queue: approve / edit / decide → label | 1,575 | 2 | 80% | 2 | 1,260 | **MUST** |
| F4 Before/after eval with money counter-metrics | 2,250 | 1 | 100% | 2 | 1,125 | **MUST** |
| F6 Langfuse monitoring dashboards | 2,250 | 0.5 | 80% | 1 | 900 | SHOULD |
| F1 Auto-decision pipeline: vision + Phi-3 + guardrail + L4/L2/L1 routing | 2,250 | 3 | 50% | 6 | 563 | **MUST** |
| F10 Self-serve claim form in the merchant dashboard | 2,250 | 1 | 50% | 3 | 375 | COULD |
| F8 Duplicate / internet-photo fraud check | 2,250 | 1 | 50% | 4 | 281 | WON'T |
| F9 File the claim with the carrier | 2,250 | 1 | 50% | 6 | 188 | WON'T |
| F7 French receipts | 675 | 0.5 | 50% | 1 | 169 | COULD |

Reach: damaged claims 2,250/month; reviewer queue = claims a person still sees ≈ 2,250 × (1 − 75% × 40%) ≈ 1,575; F7 = the FR share (≈ 30%, guess).

- **MUST (4):** F1, F2, F3, F4.
- **SHOULD:** F5 (as a separate rules release, first), F6, kill switch endpoint, BigQuery export.
- **COULD:** F7, F10, an LLM-as-judge on receipt faithfulness, test C (Kled photos).
- **WON'T this time (out of scope):**
  - real payment execution (a ledger stub instead);
  - fraud detection (F8);
  - carrier claims (F9);
  - lost parcels and cancellations;
  - merchant login and authentication;
  - automatic retraining;
  - OCR of the shipping label.
- **The feature that tests our flip assumption, and why it is a MUST:** F1 has the lowest RICE of the four MUSTs (low confidence, 6 weeks of effort). It is still a MUST because it is the only way to **measure the L4 rate with zero wrong automatic refunds**, which is condition 2 of the conditional GO.
- **The cut that hurt the most:** F5 is the highest RICE, but it is the hurdle project and needs no AI. Putting it in the AI prototype would hide whether the AI module earns its fixed costs, so it ships separately.

## 4. Data *(details in governance.md §Session 3 and DATA_MODEL_CARD.md)*

| | |
|---|---|
| Sources | Synthetic claims labelled by our policy; Bitext-derived merchant wording; Roboflow parcel photos (CC BY 4.0); Kled photo sets (optional, licensed) |
| Volume and labels | 3,000 train / 300 test A / 40 adversarial / 100 real photos, hand-labelled by 2 people with κ |
| Coverage | FR + EN, 8 item types, 6 clauses. Gap: real photos rarely show the item |
| Legal basis | Contract (art. 6(1)(b)) to decide; legitimate interest for sampling |
| Leakage | Test sets frozen, the classifier's training sets excluded |
| Freshness | Policy v1.1, versions pinned |

## 5. Model — one rung per part

| Part | Rung | Why the rung below fails |
|---|---|---|
| Intake, label facts, routing, amount | 1 rules | — (money must be deterministic and auditable) |
| Photo: damaged / normal | 3 pretrained (YOLOv11n PackageDamage) | Rules can't read pixels; no labelled claim photos to train a classical model |
| Photo: what is damaged, is the item visible | 3 pretrained (Gemini 2.5 Flash) | A two-class detector can't tell R1 from R3 from R6 |
| Clause + receipt from the evidence and free text | 3 pretrained: prompt-only Phi-3 in v0; + LoRA fine-tune only if the eval says the prompt fails | Rules can't read "carton écrasé mais le vase semble intact". Whether the prompt-only model breaks the JSON and the clause logic is what the before/after measures |
| Whole system | 4 hybrid — a **workflow** (fixed path, no loop), not an agent | An agent that picks its own steps next to a refund tool is the Chevrolet failure; our path can be drawn in advance |

## 6. Where it lives (integration surface)

| | |
|---|---|
| Surface | Merchant: a claim form with photo upload in the dashboard, and the receipt. Support: a reviewer queue (Chainlit in the prototype, the helpdesk later). Chainlit is the demo surface; FastAPI is the production surface and holds all the logic |
| Speed | < 15 s p95 per claim |
| Format | Receipt text + JSON decision |
| Fallback | Human queue; the policy function's suggestion is shown, never executed |
| Who sees the log | Merchant: the receipt. Reviewer: photo, vision outputs, model decision, policy amount, reasons. Auditor: Langfuse trace + stored receipt |

## 7. Success criterion — one sentence

> By 23 November 2026, on test A (300 synthetic claims) and test B (100 real photos), the agent resolves at least **40% of decidable damaged-parcel claims at L4** (the base rate our conditional GO needs; no L4 rate alone flips it, see the memo), with clause and amount right on ≥ 85% (A) / ≥ 75% (B) of claims — and **zero wrong automatic refunds**, with wrong refusals ≤ 2%.

## 8. Risks and rollback trigger

**Top risks:**
- Real photos rarely show the item, so there will be more R6 and fewer L4.
- Gemini can describe damage that is not there.
- The prompt-only base model may be as good as the fine-tune, in which case we orchestrate and drop the build.
- A merchant contests a receipt publicly.
- The year-1 economics lose to the rules-only project (the memo).

**Rollback trigger (one line):** over-refund leakage > **€630 per 1,000 damaged claims** or wrong refusals > **2%** in any week → `AUTONOMY_ENABLED=false`, everything is L1 from the next claim: suggestions only, a person decides and pays (owner: Head of Support).

---
*v2 only — after the users*

## 9. What the users changed

| Change | Evidence (who said / did what) |
|---|---|
| *(to fill after the three interviews and the usability test: `03_user_research.md`)* | |

## 10. What they could not decide

*(to fill: for example the €20 threshold, whether declines can ever be automatic, how much evidence a merchant must give — and who or what decides instead.)*
