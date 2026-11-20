# Data & model card · ParcelCheck (P4)

> v1, 6 Nov 2026 · Feeds `governance.md` (paste §4 into the Session 3 section) and `spec.md` §8.
> Licences marked **verify** were read from search results or the dataset page but must be re-checked on the page at download time, with the date written into `evals/MANIFEST.md`. The Roboflow pages refused automated reads (HTTP 403).

## 1. Datasets

| # | Dataset | Link | Licence | What it has | Our use | Status |
|---|---|---|---|---|---|---|
| D1 | Synthetic claims (ours) | `src/agent/generate_cases.py` | ours | Label fields + damage description + policy label; 1,500 today → 3,000 | Train, Test A | exists (template-only); Gemini paraphrase + Bitext messages to add |
| D2 | Bitext customer-support LLM training set | [HF](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset) | **CDLA-Sharing-1.0** | 26,872 synthetic Q&A rows; fields `flags, instruction, category, intent, response`; ~1,000 rows per intent | `instruction` texts of `get_refund`, `complaint`, `check_refund_policy`, `track_refund` rewritten into parcel-damage merchant messages (Gemini, fixed prompt) | public, direct download |
| D3 | Roboflow *Parcel Damage Classification* | [Universe](https://universe.roboflow.com/project-gjan7/parcel-damage-classification-sfsht) | CC BY 4.0 (verify) | Parcel photos, damaged / not | Test B | to download (free Roboflow key) |
| D4 | Roboflow *Damaged Package Detection* | [Universe](https://universe.roboflow.com/ameesh/damaged-package-detection-xjkol) | CC BY 4.0 (verify) | Boxes, damaged / food packaging | Test B | to download |
| D5 | Roboflow *Damaged Parcel Detection* | [Universe](https://universe.roboflow.com/nmd-lf3ie/damaged-parcel-detection) | CC BY 4.0 (verify) | Damaged parcels, boxes | Test B (reserve) | to download |
| D6 | Kled *Damaged Parcels, Three Frames* | [HF](https://huggingface.co/datasets/useKled/damaged-deliveries) | Kled commercial training licence | 5,000+ three-photo sets (whole item, damage close-up, packaging with label), contributor labels; JPG/PNG/HEIC | Test C, **optional** | gated: sample on request (HF form or team@kled.ai); not on HF; may not arrive in time |
| D7 | Training data v3: D4 photos described by Gemini 3.8 Flash (eu), mixed with template claims | `scripts/build_photo_training_data.py` → `data/cases_v3.jsonl` | CC BY 4.0 (D4) + ours | 1,477 rows: 1,300 template + 177 photo rows (276 photos × 2 label-fact sets, R6 photo rows capped). Damage type from Gemini's facts, **not hand-labelled**; test photos excluded by name and perceptual hash | Never trained (replaced by D8) | built 11 Nov 2026; file not kept in Git, rebuild command in `data/README.md` |
| D8 | Training data v4: v3 photo rows + templates v4 (separate EN/FR, damage that fits the item) | `src/agent/templates_v4.py`, `scripts/build_photo_training_data.py --templates v4` → `data/cases_v4.jsonl` | CC BY 4.0 (D4) + ours | 1,477 rows: 1,300 template rows (1,270 unique descriptions, 41% French, 0 mixed FR/EN) + the same 177 photo rows as v3. Template rows within 0.8 word overlap of an eval photo text are redrawn (`scripts/check_eval_leak.py`: 0 leaks vs eval v0) | Train (**M1 version 2**) | built and trained 12 Nov 2026 |
| ✗ | Roboflow *package-detection-5ozpr* (nani-tmzf6) and *package-detection-e1ssd* (roboflow-ngkro) | — | — | The training data of the YOLO model (M2) | **Excluded from every test set**, used only for the duplicate check | — |
| ✗ | Parcel3D (Zenodo) | [Zenodo](https://zenodo.org/record/8032203) | academic only, restrictive | 13k synthetic renders | Not used: licence, and renders are not claim photos | — |

### Test B build recipe (`scripts/build_test_b.py`)

1. Download D3 and D4 (D5 if short), and the two excluded YOLO training sets.
2. Compute a perceptual hash (`imagehash.phash`) of every image. Drop any D3/D4 image within Hamming distance ≤ 6 of an image in the excluded sets, and drop duplicates within D3/D4.
3. Sample 50 `damaged` and 50 `normal` images (seed 42), spread across sources. Copy them to `gs://<bucket>/images/test_b/` and record source, original id and licence.
4. For each photo, generate label fields with `generate_cases.py --fields-only --seed 2026`, plus a merchant message consistent with what a merchant would claim. In 20% of cases the merchant message contradicts the photo, on purpose.
5. **Hand labelling:** two team members label `damage_type` ∈ {content_damaged, packaging_only, no_visible_damage, unclear_photo} independently, following the guide below. We compute Cohen's κ, settle disagreements together and record the result. The target is then `policy.decide()`.

**Labelling guide:**
- `content_damaged`: the item is visible and damaged.
- `packaging_only`: the box is damaged and the item is visible and intact, *or* the item is not visible and the merchant does not claim item damage.
- `unclear_photo`: the photo is unusable, *or* the item is not visible while item damage is claimed (policy R6 v1.1).
- `no_visible_damage`: the box looks intact.

## 2. Models

| # | Model | Link | Licence | Role (rung) | Runs where | Notes |
|---|---|---|---|---|---|---|
| M1 | `microsoft/Phi-3-mini-4k-instruct` + our LoRA adapters | [HF](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct) | MIT | Decide clause, amount, receipt (fine-tuned) | Vertex AI endpoint, europe-west2, n1-standard-8 + T4 | Course model and container; `transformers==4.46.*`, `peft==0.13.2` |
| M2 | `cvtechniques/PackageDamage` (YOLOv11n, Ultralytics) | [HF](https://huggingface.co/cvtechniques/PackageDamage) | MIT (weights) · **Ultralytics library is AGPL-3.0** | Classify packaging damaged/normal (pretrained, not retrained) | Inside the FastAPI container, CPU | `best.pt`, 5.5 MB, 640×640, classes `damaged`/`normal`. Reported on its own validation set: mAP50 0.96, damaged recall 0.963, normal recall 0.876. The card says it over-predicts `damaged` on minor creases, covers cardboard boxes only (no envelopes or mailers) and is for research with a human in the loop. Pin the HF commit; `.pt` is a pickle, so load it only from the pinned commit |
| M3 | Gemini 3.8 Flash (Vertex AI, `eu` multi-region; 2.5 Flash retired 20 Oct 2026) | Vertex AI model garden | Google Cloud terms | Describe the photo (pretrained); paraphrase training text; COULD: judge receipts | Vertex AI, EU region (`GEMINI_LOCATION`) | Facts only, JSON output, `temperature=0`; version written to every trace |

### M1 versions in the Model Registry

Model `parcelcheck-phi-3-mini`, id `1379229584905469952`, europe-west2. The GCP project is **shared with the class**: other teams' models (`yoda-…`, `navy-team-…`) are in the same registry. Only touch `parcelcheck-…` resources.

| Version | Trained on | Pipeline run | Registered | Evaluated | Deployed |
|---|---|---|---|---|---|
| 1 | D1 v1, `cases.jsonl` (1,500 template rows) | `parcelcheck-phi3-refund-pipeline-20261107161606` | 7 Nov 2026 | eval v0: 39% (`evals/report_v0.md`) | undeployed (endpoint only on demo day) |
| 2 (`default` alias) | D8, `cases_v4.jsonl` (1,477 rows) | `parcelcheck-phi3-refund-pipeline-20261112120044` | 12 Nov 2026 | **not yet**: scored with v1 on `eval_set_v1.csv` in one endpoint session | never deployed |

The pipeline does not register models: `scripts/register_model_with_custom_handler.py --parent-model 1379229584905469952` adds a version. Registering makes the new version `default`, so **always pick the version explicitly** when deploying (console: open the version, then *Deploy to endpoint*). Version 2's own pipeline metrics come from its own test split (different data from v1), so they are not a before/after.

Why pretrained-only for vision: we have no labelled *claim* photos to train on. M2's measured recall is already above what we need, and test B checks it on images it never saw. Training our own detector would be the "rung above" with no evidence that it is needed.

**AGPL note for the Product decision:** using `ultralytics` in a hosted commercial service raises copyleft obligations (or needs an Ultralytics enterprise licence). For v0 (a course project) this is acceptable. For production: buy the licence, or export M2 to ONNX and run it with `onnxruntime` (Apache-2.0); the legal reading of that route has to be checked. This line goes into the build/buy discussion.

## 3. Training configuration (M1)

| Parameter | Course value | Ours | Why |
|---|---|---|---|
| Quantisation | 4-bit (QLoRA) | same | T4, 16 GB |
| LoRA r / alpha / dropout | 8 / 16 / 0.05 | same | logged with the run |
| `max_seq_length` | 64 | **1024** | Policy + claim + merchant message ≈ 600 tokens, receipt ≈ 150 |
| Batch | 16 | **4 × grad. accumulation 4** | Memory at 1024 tokens on a T4 |
| Epochs / LR | 3 / 3e-4 | 2–3 / 2e-4 | Check the validation loss in TensorBoard |
| Generation | sampled | `do_sample=False`, `max_new_tokens=300` | Deterministic decisions |
| Split | 90/10 | train 90/10 validation; tests separate (§1) | No test leakage |

## 4. Governance — Session 3 section (paste into `governance.md`)

**Six-question data audit**

1. **Provenance.**
   - Training: synthetic cases generated by our code (D1), with merchant phrasing derived from Bitext (D2, itself synthetic).
   - Test B: public Roboflow photos (D3–D5).
   - Test C: Kled contributor photos (D6), only if licensed.
   - The policy is invented.
   - Every row carries `origin`.
2. **Volume and labels.**
   - 3,000 train and 300 test A rows, labelled by the policy function (by construction, so there is no label noise and also no real-world ambiguity).
   - 40 adversarial cases, hand-written.
   - 100 test B photos, hand-labelled by 2 people, with κ reported.
   - Reviewer decisions in production become new labels.
3. **Coverage.**
   - 8 item categories, FR and EN, both covers, the 6 clauses. Class mix: 55% content damaged, 25% packaging only, 10% no damage, 10% unclear.
   - **Gaps:** real photos rarely show the item (most are box exteriors); no envelopes or plastic mailers; no languages other than FR/EN; no multi-item parcels; no claim photos with labels except Kled.
4. **Rights.**
   - D2 is CDLA-Sharing-1.0: if we publish data derived from it, we must share it under the same licence.
   - D3–D5 are CC BY 4.0: cite them in `README.md` and in the test B manifest.
   - D6 needs a signed licence before use.
   - M2 weights are MIT, but the Ultralytics code is AGPL-3.0 (see §2).
   - Gemini outputs are used under Google Cloud terms.
5. **Leakage.**
   - Test sets are never used for training or tuning.
   - Test A uses a different seed, held-out item words and a different paraphrase prompt.
   - Test B excludes YOLO's training sets and their near-duplicates (pHash).
   - The prompt is frozen before test B is opened.
   - Every look at a test set is logged in `evals/CHANGELOG.md`.
6. **Freshness.**
   - The policy is versioned (v1.1). Any policy change regenerates the labels and the fine-tune, and test A/B are re-run.
   - Model versions are pinned (Phi-3 registry version, YOLO commit, Gemini model id). A provider-side Gemini change triggers a re-run before L4 is re-enabled.

**Purpose and retention.**
- Purpose: deciding damaged-parcel refund claims and auditing them.
- Photos and traces are kept 90 days.
- Decisions and receipts (the audit log) are kept as long as accounting rules require [owner to confirm].
- Reviewer labels are kept for retraining.

**Isolation between customers.**
- Every record has a `merchant_id`. The reviewer queue and the APIs filter by it.
- No merchant's data appears in another merchant's prompt: there are no few-shot examples from production data.

**Personal data.**
- Merchant messages are redacted (email, phone) before Gemini, Phi-3 and Langfuse.
- Label photos are never sent to a third-party model in v0.
- Test data contains no real customer data.

**Gaps by segment to watch.** Content-damage claims on real photos, French messages, premium cover (20% of data), fragile items without the option.

**Trust level per step.** As in `spec.md` §3: vision steps have no autonomy; Phi-3 decides; rules route; L4 ≤ €20 only if every check passes; L2 €20–100; L1 above €100 or on any incoherence. Every decline needs a person.

**Owner and rollback.** Product owner: [name]. Rollback trigger and lever: `spec.md` §12.
