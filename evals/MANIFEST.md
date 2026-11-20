# Test-set manifest

Every frozen test set: where it comes from, its licence, when it was built, and a hash so any later change shows.
Never train or tune on these files. Log every look in the report that used it.

## Photo set v0 (`evals/photo_set_v0.csv`)

| Field | Value |
|---|---|
| Built | 2026-11-07, `scripts/build_test_b.py`, seed 42 |
| Rows | 100 photos: 50 `damaged`, 50 `normal` (label from the dataset's own folders) |
| CSV sha256 | `3106b0d08419dbecb3c952ecb8019511a34069e87b7f81ffe91ab135f73b7181` |
| Images | not in git (`evals/photos/` is ignored), copied to `gs://<bucket>/images/test_b/` |
| Excluded | food boxes (`--exclude-class food`), 3 near-duplicates (perceptual hash, distance ≤ 6) |
| Not yet done | duplicate check against the YOLO training sets (not downloaded); our own photos (`--own`) |

### Source

| | |
|---|---|
| Dataset | Damaged Package Detection, v1 (D4 in `DATA_MODEL_CARD.md`) |
| Author | ameesh (Roboflow Universe) |
| Link | https://universe.roboflow.com/ameesh/damaged-package-detection-xjkol |
| Licence | CC BY 4.0. **Verify on the page and write the date here:** read on ____ by ____ |
| Downloaded | 2026-11-07, via a fork in our Roboflow workspace, "folder" export, no augmentation |
| Classes used | `packaging boxes that are damaged`, `damaged` → damaged · `packaging boxes` → normal |

Attribution (CC BY 4.0): "Damaged Package Detection" by ameesh, Roboflow Universe, CC BY 4.0.

## Photo set v1 (`evals/photo_set_v1.csv`)

| Field | Value |
|---|---|
| Built | 2026-11-07, `scripts/build_test_b.py --seed 43 --id-prefix PB --exclude-csv evals/photo_set_v0.csv` |
| Rows | 100 photos (PB001–PB100): 50 `damaged`, 50 `normal` by the dataset's folders. None of them in v0 |
| CSV sha256 | `27e781eae1534fef6ccd1a53a4cbac2e11ac1c13efd862d103684017d0576931` |
| Images | not in git, `evals/photos/v1/` → `gs://<bucket>/images/test_b_v1/` |
| Source | same as v0 (D4, ameesh, CC BY 4.0) |
| Used for | prompt v1, measured once (`photo_report_v1.md`); not tuned on |

## Product eval set v0 (`evals/eval_set_v0.csv`)

| Field | Value |
|---|---|
| Rows | 50 (EV01–EV50), origin `invented`, labels from `policy.py` v1.1 |
| CSV sha256 (first model run, 7 Nov 2026) | `2326cef9770961b8a098920ab2792aa0c7e12ba045e3076d23cf636e215bb955` |
| CSV sha256 (after hand check, 11 Nov 2026) | `f7efab8ad39f3d5f7269d8126f766abc51e91acfa62bf5cf4505e35a1f457a5a` |
| Hand check | 11 Nov 2026, Luli, all 50 rows (`evals/label_check.md`): 0 disagreements. Only `notes` (initials + date) and `origin` ("to check by hand" → "checked by hand") changed; **no input or label changed** |
| First model run | 7 Nov 2026, fine-tuned Phi-3 endpoint (`report_v0.md`) |
