# 03 — AI Lean Canvas · ParcelCheck, damaged-parcel refund agent (P4)

> One screen. Nine blocks from the classic Lean Canvas (Ash Maurya) + five AI blocks. Short phrases, from 01, 02 and 03.

## The nine classic blocks

| Block | Our answer | Comes from |
|---|---|---|
| 1. Problem — top 3 pains | Every refund takes the same 12–17 min, even a €4.90 one · photo + label + policy in three tools · merchants wait 3 days | 01 |
| 2. Users / customer segments | Refund agents (the reviewer queue) · merchants shipping parcels (claimants) · Finance (leakage) | 01 (persona) |
| 3. Unique value proposition | A damaged-parcel refund decided in a minute, with a receipt that says exactly why: the same text for the merchant and the audit | 01 (press release) |
| 4. Solution — the MUST features | Auto-decision pipeline with L4/L2/L1 routing · decision receipt · reviewer queue · before/after eval with money counter-metrics | 03 brief §3 |
| 5. Channels — where it lives | Claim form in the merchant dashboard · reviewer queue for support (Chainlit prototype → helpdesk) · FastAPI service | 03 brief §6 |
| 6. Value — per year | Year 1 base +€117k, EV +€121k (pessimistic −€91k); below the €159k hurdle → conditional GO on the AI module | 02 |
| 7. Cost structure — seven lines | Tokens ≈ €0.5k · integration €30k/yr (amortised) · evaluation €20k · supervision €13.5k · monitoring + endpoint €22k · re-evaluation €12k · error cost 3% × €35 on L4 | 02 |
| 8. Key metric | ≥ 40% of decidable damaged claims at L4 with zero wrong automatic refunds (test A + B, 23 Nov) | 03 brief §7 |
| 9. Unfair advantage | Label, cover and tracking data no vendor sees; our policy is code; eval-sets and adapters we own | 02 (build / buy) |

## The five AI blocks

| Block | Our answer | Comes from |
|---|---|---|
| 10. Data — sources, rights, gaps | Synthetic claims (policy-labelled) · Bitext wording (CDLA-Sharing) · Roboflow photos (CC BY 4.0) · Kled optional (licensed). Gap: few real photos show the item | governance.md · S3 |
| 11. Model — rung per part | Rules (facts, amount, routing) · YOLOv11n pretrained · Gemini pretrained · Phi-3 prompt-only in v0, + LoRA only if the eval says so · hybrid workflow overall, not an agent | 03 brief §5 |
| 12. Evaluation — eval-set and size | `evals/eval_set_v0.csv` 20 → 50 cases · test A 300 · adversarial 40 · test B 100 real photos (2 labellers, κ) · base vs fine-tuned | evals/ |
| 13. Human in the loop | L4 ≤ €20 with a 5% weekly sample · L2 €20–100 and every decline · L1 > €100, unclear photos, any incoherence · kill switch → all L1, owner Head of Support | 03 brief §2 · governance.md S4 |
| 14. Risks & governance | Never pay an amount the policy does not give · rollback at €630 leakage per 1,000 claims or > 2% wrong refusals · limited-risk tier, AI disclosed on the receipt | governance.md |
