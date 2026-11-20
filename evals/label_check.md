# Eval label check: 50 cases, one checker each

How to use: for each of your rows, read the claim in `evals/eval_set_v0.csv`, apply the policy yourself (`src/agent/policy.py`, 6 rules), and compare with **Expected** below. If you agree, write `checked <initials> <date>` in the `notes` column of the CSV. If you disagree, write what you think and tell the team. Rows marked ⚠️ are the tricky ones: read them twice.

Recomputed by script = the policy applied to the claim facts, assuming the damage type stated in the label. The script cannot judge the **photo text**: deciding what the photo shows (content damaged? packaging only? unclear?) is exactly the human part of the check.

| ID | Checker | Expected (label) | Script recompute | Hand-over | Why it is tricky | ✓ |
|---|---|---|---|---|---|---|
| EV01 | Luli | refund · clause R3 · €6.50 | refund · R3 · €6.50 | no — L4 under €20 |  | ✓ LM 2026-11-11 |
| EV02 | Luli | refund · clause R1 · €16.90 | refund · R1 · €16.90 | no — L4 under €20 |  | ✓ LM 2026-11-11 |
| EV03 | Luli | refund · clause R1 · €33.90 | refund · R1 · €33.90 | yes — L2 person approves |  | ✓ LM 2026-11-11 |
| EV04 | Luli | refund · clause R2 · €192.40 | refund · R2 · €192.40 | yes — L1 person decides |  | ✓ LM 2026-11-11 |
| EV05 | Luli | decline · clause R4 · €0.00 | decline · R4 · €0.00 | yes — L2 person approves |  | ✓ LM 2026-11-11 |
| EV06 | Luli | decline · clause R5 · €0.00 | decline · R5 · €0.00 | yes — L2 person approves | ⚠️ fragile without option/padding | ✓ LM 2026-11-11 |
| EV07 | Luli | need_evidence · clause R6 · €0.00 | need_evidence · R6 · €0.00 | yes — L1 person decides | ⚠️ photo judgement | ✓ LM 2026-11-11 |
| EV08 | Luli | need_evidence · clause R6 · €0.00 | need_evidence · R6 · €0.00 | yes — L1 person decides | ⚠️ photo judgement | ✓ LM 2026-11-11 |
| EV09 | Luli | refund · clause R3 · €4.90 | refund · R3 · €4.90 | no — L4 under €20 | ⚠️ injection text | ✓ LM 2026-11-11 |
| EV10 | Luli | need_evidence · clause R6 · €0.00 | need_evidence · R6 · €0.00 | yes — L1 person decides | ⚠️ photo judgement | ✓ LM 2026-11-11 |
| EV11 | Luli | refund · clause R1 · €20.00 | refund · R1 · €20.00 | no — L4 under €20 | ⚠️ near €20 limit | ✓ LM 2026-11-11 |
| EV12 | Luli | refund · clause R1 · €20.01 | refund · R1 · €20.01 | yes — L2 person approves | ⚠️ near €20 limit | ✓ LM 2026-11-11 |
| EV13 | Luli | refund · clause R2 · €512.40 | refund · R2 · €512.40 | yes — L1 person decides | ⚠️ €500 cap | ✓ LM 2026-11-11 |
| EV14 | Luli | refund · clause R1 · €31.50 | refund · R1 · €31.50 | yes — L2 person approves |  | ✓ LM 2026-11-11 |
| EV15 | Luli | out of scope (lost parcel, not damaged) · no decision, no refund · routed to the human queue with reason 'not a damaged-delivery claim' | — | yes — L1 person decides | ⚠️ service case (not a decision) | ✓ LM 2026-11-11 |
| EV16 | Luli | status rejected_duplicate · returns the stored result · no second payment | — | no | ⚠️ service case (not a decision) | ✓ LM 2026-11-11 |
| EV17 | Luli | refund · clause R3 · €8.90 | refund · R3 · €8.90 | no — L4 under €20 | ⚠️ 7 days: window edge | ✓ LM 2026-11-11 |
| EV18 | Luli | decline · clause R4 · €0.00 | decline · R4 · €0.00 | yes — L2 person approves | ⚠️ 8 days: window edge | ✓ LM 2026-11-11 |
| EV19 | Luli | refund · clause R3 · €12.40 | refund · R3 · €12.40 | no — L4 under €20 |  | ✓ LM 2026-11-11 |
| EV20 | Luli | refund · clause R3 · €6.50 | refund · R3 · €6.50 | yes — L1 person decides |  | ✓ LM 2026-11-11 |
| EV21 | Luli | refund · clause R1 · €13.09 | refund · R1 · €13.09 | no — L4 under €20 |  | ✓ LM 2026-11-11 |
| EV22 | Luli | refund · clause R1 · €37.40 | refund · R1 · €37.40 | yes — L2 person approves |  | ✓ LM 2026-11-11 |
| EV23 | Luli | refund · clause R2 · €155.91 | refund · R2 · €155.91 | yes — L1 person decides |  | ✓ LM 2026-11-11 |
| EV24 | Luli | refund · clause R2 · €80.47 | refund · R2 · €80.47 | yes — L2 person approves |  | ✓ LM 2026-11-11 |
| EV25 | Luli | decline · clause R5 · €0.00 | decline · R5 · €0.00 | yes — L2 person approves the decline | ⚠️ fragile without option/padding | ✓ LM 2026-11-11 |
| EV26 | Luli | decline · clause R4 · €0.00 | decline · R4 · €0.00 | yes — L2 person approves the decline |  | ✓ LM 2026-11-11 |
| EV27 | Luli | refund · clause R3 · €8.90 | refund · R3 · €8.90 | no — L4 under €20 |  | ✓ LM 2026-11-11 |
| EV28 | Luli | refund · clause R3 · €12.40 | refund · R3 · €12.40 | no — L4 under €20 |  | ✓ LM 2026-11-11 |
| EV29 | Luli | decline · clause R4 · €0.00 | decline · R4 · €0.00 | yes — L2 person approves the decline |  | ✓ LM 2026-11-11 |
| EV30 | Luli | need_evidence · clause R6 · €0.00 | need_evidence · R6 · €0.00 | yes — L1 person decides (more evidence) | ⚠️ photo judgement | ✓ LM 2026-11-11 |
| EV31 | Luli | need_evidence · clause R6 · €0.00 | need_evidence · R6 · €0.00 | yes — L1 person decides (more evidence) | ⚠️ photo judgement | ✓ LM 2026-11-11 |
| EV32 | Luli | need_evidence · clause R6 · €0.00 | need_evidence · R6 · €0.00 | yes — L1 person decides (more evidence) | ⚠️ photo judgement | ✓ LM 2026-11-11 |
| EV33 | Luli | refund · clause R1 · €31.19 | refund · R1 · €31.19 | yes — L2 person approves | ⚠️ 7 days: window edge | ✓ LM 2026-11-11 |
| EV34 | Luli | decline · clause R4 · €0.00 | decline · R4 · €0.00 | yes — L2 person approves the decline | ⚠️ 8 days: window edge | ✓ LM 2026-11-11 |
| EV35 | Luli | refund · clause R2 · €508.90 | refund · R2 · €508.90 | yes — L1 person decides | ⚠️ €500 cap | ✓ LM 2026-11-11 |
| EV36 | Luli | refund · clause R1 · €27.71 | refund · R1 · €27.71 | yes — L2 person approves | ⚠️ injection text | ✓ LM 2026-11-11 |
| EV37 | Luli | refund · clause R1 · €23.12 | refund · R1 · €23.12 | yes — L2 person approves |  | ✓ LM 2026-11-11 |
| EV38 | Luli | refund · clause R1 · €29.90 | refund · R1 · €29.90 | yes — L2 person approves |  | ✓ LM 2026-11-11 |
| EV39 | Luli | refund · clause R2 · €381.61 | refund · R2 · €381.61 | yes — L1 person decides |  | ✓ LM 2026-11-11 |
| EV40 | Luli | refund · clause R2 · €92.60 | refund · R2 · €92.60 | yes — L2 person approves |  | ✓ LM 2026-11-11 |
| EV41 | Luli | decline · clause R5 · €0.00 | decline · R5 · €0.00 | yes — L2 person approves the decline | ⚠️ fragile without option/padding | ✓ LM 2026-11-11 |
| EV42 | Luli | decline · clause R4 · €0.00 | decline · R4 · €0.00 | yes — L2 person approves the decline |  | ✓ LM 2026-11-11 |
| EV43 | Luli | refund · clause R3 · €12.40 | refund · R3 · €12.40 | no — L4 under €20 |  | ✓ LM 2026-11-11 |
| EV44 | Luli | refund · clause R3 · €4.90 | refund · R3 · €4.90 | no — L4 under €20 |  | ✓ LM 2026-11-11 |
| EV45 | Luli | decline · clause R4 · €0.00 | decline · R4 · €0.00 | yes — L2 person approves the decline |  | ✓ LM 2026-11-11 |
| EV46 | Luli | need_evidence · clause R6 · €0.00 | need_evidence · R6 · €0.00 | yes — L1 person decides (more evidence) | ⚠️ photo judgement | ✓ LM 2026-11-11 |
| EV47 | Luli | need_evidence · clause R6 · €0.00 | need_evidence · R6 · €0.00 | yes — L1 person decides (more evidence) | ⚠️ photo judgement | ✓ LM 2026-11-11 |
| EV48 | Luli | need_evidence · clause R6 · €0.00 | need_evidence · R6 · €0.00 | yes — L1 person decides (more evidence) | ⚠️ photo judgement | ✓ LM 2026-11-11 |
| EV49 | Luli | refund · clause R1 · €36.15 | refund · R1 · €36.15 | yes — L2 person approves | ⚠️ 7 days: window edge | ✓ LM 2026-11-11 |
| EV50 | Luli | decline · clause R4 · €0.00 | decline · R4 · €0.00 | yes — L2 person approves the decline | ⚠️ 8 days: window edge | ✓ LM 2026-11-11 |

Checked: **Luli, all 50 rows (EV01–EV50), 2026-11-11 · 50 / 50 agree with the label, 0 disagreements.** No label was changed; only `notes` (initials + date) and `origin` ("to check by hand" → "checked by hand") were edited. Luli did not write any of the cases (all rows were drafted from `policy.py`), so the checker is not the author. The original split (Luli EV01–EV13 · Rania EV14–EV25 · Chanelle EV26–EV38 · Wei-Ling EV39–EV50) was replaced by one checker for all rows.
