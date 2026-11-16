# Photo test v0: Gemini on real photos

Run 2026-11-07 · model `gemini-3.8-flash` · prompt v0 (frozen) · 100 photos (100 public with a dataset label, 0 our own) · errors: 0

Gemini only describes; this checks that the facts it reads from a real photo are right. The decision and the amount are checked separately (`report_v0.md`).

## 1. Packaging damage vs the dataset label (public photos)

| | Result |
|---|---|
| Damaged photos seen as damaged (recall) | 33/50 (66%) |
| Normal photos seen as intact | 29/50 (58%) |
| Overall agreement | 62/100 (62%) |
| Marked unusable | 31/100 (31%) |

## 2. damage_type vs our hand label

Agreement: **n/a**. Seen as `content_damaged` when the hand label says otherwise (the error that would pay money): **0**. Unclear photos not flagged: **0**.

| Hand label → predicted | Count |
|---|---|

## 3. Rows to look at


## Reading it (7 Nov 2026, Wei-Ling)

**1. The public set is noisy.** 29 of the 31 photos marked unusable are not parcel photos: assembly diagrams
(PH001), marketing mock-ups (PH010, PH011), studio product shots (PH012, PH019), 3D renders (PH038).
Gemini was right to flag them; the Roboflow folder labels are wrong for our use. Part 1 therefore
undercounts Gemini, and hand labels (part 2) are needed before any number is quoted as "accuracy".

**2. One miss comes from our own prompt.** Of the 21 intact photos read as damaged, almost all are open,
empty, intact boxes (PH002, PH009, PH021, PH022, PH032, ...). Gemini's own descriptions say "intact, no dents
or tears", but prompt v0 defined damaged packaging as "dented, crushed, torn, wet **or open**". A merchant
always opens the parcel before claiming, so "open" must not count as damage.

**On real photos only (69 Gemini judged usable):** damaged seen as damaged 31/35 (89%); intact seen as
intact 13/34 (38%), pulled down by the "open" rule.

**What it means for the trust levels (`spec.md`).** The costly error is "damage seen where there is none".
Here it is packaging damage, which by itself only pays the label fee (R3); item damage needs the item to be
visible. Unusable photos go to R6 → a person (L1), as designed. Nothing here changes the routing; it changes
the prompt.

**What we change.** Prompt v1: an opened, intact box is not damaged (`src/agent/vision.py`, `PROMPT_VERSION`).
We do **not** rerun v1 on these 100 photos: we have looked at them, so a better score here would be tuning on
the test. v1 is checked on a fresh, disjoint sample (`photo_set_v1.csv`, seed 43, `--exclude-csv` this set)
and on our own photos. Logged in `evals/CHANGELOG.md`.

- Origin of every photo is in `photo_set_v0.csv` (`real-public`, D4, CC BY 4.0). No customer photos.
