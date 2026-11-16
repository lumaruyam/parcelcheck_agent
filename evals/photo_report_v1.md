# Photo test: Gemini on real photos (photo_set_v1.csv, prompt v1)

Run 2026-11-07 · model `gemini-3.8-flash` · prompt v1 · 100 photos (100 public with a dataset label, 0 our own) · errors: 0

Gemini only describes; this checks that the facts it reads from a real photo are right. The decision and the amount are checked separately (`report_v0.md`).

## 1. Packaging damage vs the dataset label (public photos)

| | Result |
|---|---|
| Damaged photos seen as damaged (recall) | 27/50 (54%) |
| Normal photos seen as intact | 50/50 (100%) |
| Overall agreement | 77/100 (77%) |
| Marked unusable | 35/100 (35%) |

Usable photos only (what Gemini judged to be a real parcel photo):

| | Result |
|---|---|
| Damaged seen as damaged | 24/37 (65%) |
| Intact seen as intact | 28/28 (100%) |

## 2. damage_type vs our hand label

Agreement: **n/a**. Seen as `content_damaged` when the hand label says otherwise (the error that would pay money): **0**. Unclear photos not flagged: **0**.

| Hand label → predicted | Count |
|---|---|

## 3. Rows to look at


## Reading it (7 Nov 2026, Wei-Ling)

Fresh sample: 100 photos never looked at before (seed 43, the 100 photos of v0 excluded). Prompt v1.

**The fix worked.** Intact photos read as intact went from 13/34 (v0) to **28/28** on real photos: an opened
box is no longer called damaged.

**"Damaged seen as damaged" 24/37 is mostly the dataset, not Gemini.** We opened 6 of the 13 misses by eye
(PB007, PB055, PB062, PB084, PB087, PB088):
- 5 are intact boxes (open, sealed or new) filed under "packaging boxes that are damaged" in the public set;
- PB087 is an intact box with a **broken dish inside**: Gemini reported the item as damaged, which is correct,
  and is exactly the case R1 pays for. It only counts as a "miss" here because part 1 checks the box.

So on the photos we checked, Gemini made no error. The dataset's folder labels cannot be used as the truth,
and 35 of 100 images are not parcel photos at all (stock shots, infographics, cartoons, a scanner image).

**What it means.** No accuracy figure is quoted from part 1. The number we report comes from part 2, after two
of us hand-label `photo_set_v1.csv` independently (labelling guide in `DATA_MODEL_CARD.md`, Cohen's κ), and
from our own phone photos, which look like real claims. Non-photos go to R6 → a person (L1), as designed.

- Origin of every photo is in `photo_set_v1.csv` (`real-public`, D4, CC BY 4.0). No customer photos.
