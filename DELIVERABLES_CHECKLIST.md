# Deliverables checklist · Data & AI Product (MSA-DAT07-04)

Built from the course templates (`project_repo_template`, `S3_templates` to `S8_templates`, `S_Recap_Sessions_1_to_7`).
A box is ticked only when the file is **merged on `main`** of this repo.

**Status on 25 Nov 2026:** ✅ on `main` · ⬜ to do. Rounds P1–P4 and R1–R4 and #30 (S8 files, A5 wording, eval set v1, this checklist) are merged. Pre-tag check 25 Nov (Wei-Ling): authors per file, secrets, placeholders, drill wording.

## Key dates

| Date | What |
|---|---|
| Sun 22 Nov, 23:59 | Assignment 5: `05_metrics.md`, eval set v1, judge kit with the two agreement rates, governance S5 |
| Mon 23 Nov | `06_07_experiments_operations.md`, governance S6 and S7 |
| Tue 24 Nov | optional pitch rehearsal in class (8 min + 3 min feedback, not graded) |
| Thu 26 Nov | `08_launch_memo.md`, governance S8 line, final `spec.md` and `03_product_brief.md`, then **`git tag v1.0`** |
| Fri 27 Nov | Pitch: 8 min + 3 min questions, **everyone speaks**. No commits after the first oral starts |

## Repo rules (checked at the oral)

- [x] Every member authors commits in **at least four numbered files**, with their own Git account ✅ (Chanelle 7 · Luli 5 · Rania 5 · Wei-Ling 5)
- [x] No `.env`, keys, tfvars or real photos committed: checked 25 Nov on `main` (no `.env` or tfvars tracked, no key patterns; the only images are the four screenshots in `docs/`). Re-check after any later merge
- [ ] `v1.0` tag pushed on 26 Nov; nothing pushed after the first oral starts
- [x] Pitch slides and demo video are **not** in Git

Check the authors before the tag: `git log --no-merges --format='%an' -- <file> | sort -u`, file by file.

## Assignment 1–2 · problem, sizing, investment (S1–S2)

- [x] `01_problem_statement.md`
- [x] `02_sizing.xlsx`
- [x] `02_investment_memo.md`: how much, how sure, what if we're wrong, compared to what
- [x] `governance.md` S1 (six questions) and S2 (cost of error)

## Assignment 3 · MVP brief and design loop (S3)

- [x] `03_product_brief.md` v2: §9 "What the users changed" (each change with its evidence), §10 "What they could not decide"
- [x] `03_ai_lean_canvas.md`: nine blocks + the five AI blocks (10–14)
- [x] `03_user_research.md`: three 20-min conversations, usability test, "what we heard" rows 1–14
- [x] `03_prototype_link.md`: link, prompt, screenshot `docs/prototype_v0.1.png`
- [x] `spec.md` (v3)
- [x] `evals/eval_set_v0.csv`: 50 labelled cases, label check, `DATA_MODEL_CARD.md`
- [x] `governance.md` S3: six-question data audit, trust level per step

## Assignment 4 · prototype and architecture (S4)

- [x] `/prototype`: four steps chained, Chainlit app with chat and claim history
- [x] `04_architecture.md` v1.3 (Parts A and B)
- [x] `evals/report_v0.md`: 39 % L4 vs 40 %, 0 wrong automatic refunds, clause 92 %, valid JSON 96 %, switch test
- [x] `spec.md` v3: every eval miss becomes a line
- [x] `governance.md` S4: checkpoints ⊘, switch owner ⏻, where eval data lives
- [x] CI: the eval-set test now runs (`eval_set_v0.csv` is on `main`, the skip no longer applies)

## Assignment 5 · metrics and evaluation plan (S5) · due 22 Nov

- [x] `05_metrics.md` §1–5 (§1, 2, 4 Rania · §3 Luli · §5 Chanelle)
- [x] `05_metrics.md`: the two judge rates, written as *not measured yet* (billing blocked since 17 Nov), with the procedure
- [x] `evals/eval_set_v1.csv`: **100 cases**, stratified by segment, synthetic rows tagged, labels checked by hand (Wei-Ling, 20 Nov; V063–V072 relabelled R6), leak check 0
- [x] `evals/judge_rubric.md` + `evals/judge_prompt.txt`
- [x] `evals/report_v1.md`: eval v1 on the endpoint, 25 Nov (Wei-Ling): 18 % L4 and 3 wrong automatic refunds → R3 guardrail fix (No.31) → 10 % and 0; criterion not met, gate stays closed
- [ ] `evals/README.md`: the **two agreement rates on 30 cases** — *not measured yet*: billing restored 25 Nov and the receipts exist; grading (Luli, Rania) not done before the tag
- [x] `governance.md` S5: counter-metrics, segments reported, harm threshold, owner

## Assignments 6–7 · experiments and operations (S6–S7) · due 23 Nov

- [x] `06_07_experiments_operations.md` §1–5 (§1–2 Luli · §3–5 Wei-Ling), sample size in `evals/sample_size.ipynb`
- [x] The six questions answered: comparison group · unit (merchant) · smallest gain (€3) · slowest guardrail (4 weeks) · decision rule written before · plan B
- [x] `06_07` §4.3 "Last tested": 20 Nov switch re-run; drill role-played before the tag (switch off/on; label rollback and timing not covered)
- [x] `governance.md` S6 and S7

## Session 8 · launch and pitch · due 26 Nov

- [x] `08_launch_memo.md` in the **six parts of the S8 template**
- [x] `08_launch_memo.md`: dates filled (shadow 1–12 Feb 2027, A/B read 15 Mar 2027, drill role-played, not timed); judge rates *not measured yet* (billing)
- [x] `governance.md` S8 line: who signs, AI disclosure, last rollback test
- [x] Final `spec.md` (v3) and `03_product_brief.md` (v2) on `main` (re-check after the last changes)
- [x] `README.md` AI Product section and this checklist (R4-W, #30)
- [ ] `git tag v1.0` and `git push origin v1.0` ⬜

## Work that is not a file

- [x] Eval v1 checked row by row (Wei-Ling, 20 Nov); Chanelle reads the 29 flagged rows and the 10 relabels before the oral (Q3)
- [ ] Two graders who did not write the cases grade the 30 golden rows → human–human rate
- [ ] Judge run on the same 30 rows → human–judge rate (billing restored 25 Nov; waits for the human grades)
- [x] Switch re-run 20 Nov (scripted): switch off 0 L4 of 48 and of 90; switch on 12 of 48
- [x] Switch drill role-played by Rania and Wei-Ling (switch off → claim to a person → switch on); **still to do:** prompt-label rollback and a timed run
- [ ] Time study: is one damaged claim ≥ €17.50 by hand? (3 interviews + 30 replayed claims)
- [x] Endpoint undeployed (20 Nov)

## Pitch (27 Nov, not on Git)

- [x] Slides: 10-slide plan of S8 slide 6, with speaker notes (Claude Slides deck)
- [x] The five graded points covered; each slide has a speaker; 8 questions have an owner (pitch prep doc)
- [ ] Demo video recorded in offline mode (`GCP_ENDPOINT_ID= INPUT_GUARDRAIL=false`): a normal case, a refused case, the score
- [ ] Three timed rehearsals; the last one at 7 minutes
