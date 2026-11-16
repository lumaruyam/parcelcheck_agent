"""Training data v3: real photos described by Gemini, mixed with template claims (no retraining here).

Why: at runtime Phi-3 reads Gemini's description of the merchant's photo, but v1 was trained on our
15 template sentences. v3 trains on the same kind of text it will read (report_v0.md §3, miss 1).

    uv run --with imagehash --with pillow python -m scripts.build_photo_training_data \
        --source "$HOME/Downloads/Damaged Package Detection.v1-v1.folder" --exclude-class food

1. Lists the photos, drops every photo already used in a test set (photo_set_v0/v1, by name) and any
   near-duplicate of a test photo (perceptual hash), so no test photo leaks into training.
2. Gemini (src/agent/vision.describe_facts, the app's own call) describes each photo once.
   Cached in data/photo_descriptions.jsonl: a rerun only calls Gemini for new photos.
3. Each photo gets --combos sets of random label facts (cover, value, fee, days, options); the damage
   type comes from Gemini's facts (same rule as the app), the answer from policy.py.
4. Template claims are added so photos are about --photo-share of the rows (default 1/3); templates
   keep every rule R1-R6 covered. Output: data/cases_v3.jsonl (same format as cases.jsonl).
Cost: one Gemini call per new photo (about $0.0015 with 3.8 Flash), nothing else.
"""
import argparse
import csv
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import src.agent.generate_cases as gc
from scripts.build_test_b import images, label_from_path
from src.agent.generate_cases import ITEM_WORD, ITEMS, to_example
from src.agent.policy import Case
from src.agent.vision import damage_type_from_facts

CATEGORY_WORDS = {  # guess the item from Gemini's words; random category if nothing matches
    "ceramics": r"\b(mug|cup|plate|bowl|ceramic|dish|teapot)\b",
    "glassware": r"\b(glass|vase|bottle|jar)\b",
    "electronics": r"\b(phone|headphone|laptop|tablet|camera|electronic|speaker|keyboard|mouse|console|charger)\w*",
    "cosmetics": r"\b(perfume|cosmetic|lipstick|cream|makeup|skincare|serum)\w*",
    "clothing": r"\b(shirt|jacket|dress|clothing|sweater|jeans|t-shirt|apparel)\w*",
    "books": r"\b(book|books|notebook|magazine)\b",
    "toys": r"\b(toy|toys|lego|doll|puzzle|game)\b",
    "shoes": r"\b(shoe|shoes|sneaker|boot|boots|trainer)s?\b",
}


def guess_category(text: str, rng: random.Random) -> str:
    for cat, pattern in CATEGORY_WORDS.items():
        if re.search(pattern, text, re.I):
            return cat
    return rng.choice(list(ITEM_WORD))


def photo_case(i: int, k: int, photo_id: str, facts: dict, rng: random.Random) -> dict:
    """One training row: random label facts + Gemini's description and damage type."""
    cat = guess_category(facts["description"], rng)
    fragile, (lo, hi) = next((f, r) for c, f, r in ITEMS if c == cat)
    case = Case(
        case_id=f"P{i:04d}-{k}", cover=rng.choices(["standard", "premium"], [0.8, 0.2])[0],
        item_category=cat, fragile_item=fragile,
        fragile_option=rng.random() < (gc.FRAGILE_OPTION_RATE if fragile else 0.1),
        padding=rng.random() < 0.8, item_value_eur=round(rng.uniform(lo, hi), 2),
        label_fee_eur=rng.choice([4.9, 6.5, 8.9, 12.4]),
        days_since_delivery=rng.choices([rng.randint(0, 7), rng.randint(8, 30)], [0.85, 0.15])[0],
        damage_type=damage_type_from_facts(facts), damage_description=facts["description"],
    )
    row = to_example(case)
    row.update(origin="photo-gemini", photo=photo_id, photo_source=facts.get("source", ""),
               photo_licence=facts.get("licence", ""), gemini_model=facts.get("model", ""))
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="Roboflow folder export (class = folder name)")
    ap.add_argument("--source-name", default="D4-roboflow-damaged-package-detection")
    ap.add_argument("--licence", default="CC BY 4.0")
    ap.add_argument("--exclude-class", action="append", default=[])
    ap.add_argument("--test-csv", action="append", default=["evals/photo_set_v0.csv", "evals/photo_set_v1.csv"])
    ap.add_argument("--test-photos", default="evals/photos", help="folder of test images, for the near-duplicate check")
    ap.add_argument("--max-hamming", type=int, default=6)
    ap.add_argument("--max-photos", type=int, default=0, help="0 = all remaining photos")
    ap.add_argument("--combos", type=int, default=2, help="label-fact sets per photo")
    ap.add_argument("--photo-share", type=float, default=1 / 3)
    ap.add_argument("--n-templates", type=int, default=0,
                    help="fixed number of template rows (overrides --photo-share), e.g. 1300")
    ap.add_argument("--photo-r6-ratio", type=float, default=0,
                    help="cap photo rows that end in R6 at this multiple of the other photo rows (0 = no cap)")
    ap.add_argument("--fragile-option-rate", type=float, default=0.45, help="0.45 = R5 boost, as in data v2")
    ap.add_argument("--templates", choices=["v1", "v4"], default="v1",
                    help="v4 = varied EN/FR wording (src/agent/templates_v4.py), after Luli's eval check of 11 Nov")
    ap.add_argument("--eval-csv", action="append", default=["evals/eval_set_v0.csv"],
                    help="eval sets whose photo descriptions must not appear in training (v4: rows too close are redrawn)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cache", default="data/photo_descriptions.jsonl")
    ap.add_argument("--out", default="data/cases_v3.jsonl")
    ap.add_argument("--stub", action="store_true", help="no Gemini: fake facts from the folder name (dry run)")
    a = ap.parse_args()
    gc.FRAGILE_OPTION_RATE = a.fragile_option_rate
    rng = random.Random(a.seed)

    # 1. photos, minus the test sets (by name and by near-duplicate)
    used = set()
    for p in a.test_csv:
        if Path(p).exists():
            used |= {r["original_name"] for r in csv.DictReader(open(p, encoding="utf-8"))}
    test_hashes = []
    if Path(a.test_photos).exists():
        import imagehash
        from PIL import Image

        def phash(path):
            with Image.open(path) as im:
                return imagehash.phash(im.convert("RGB"))

        test_hashes = [phash(p) for p in images(Path(a.test_photos))]
    photos, skipped = [], Counter()
    for p in images(Path(a.source).expanduser()):
        if any(x.lower() in p.parent.name.lower() for x in a.exclude_class):
            skipped["excluded_class"] += 1
            continue
        if p.name in used:
            skipped["in_a_test_set"] += 1
            continue
        if test_hashes and any(phash(p) - h <= a.max_hamming for h in test_hashes):
            skipped["near_duplicate_of_test"] += 1
            continue
        photos.append(p)
    rng.shuffle(photos)
    if a.max_photos:
        photos = photos[: a.max_photos]
    print(f"{len(photos)} training photos; skipped {dict(skipped)}")

    # 2. Gemini descriptions, cached
    cache = {}
    if Path(a.cache).exists():
        cache = {r["photo"]: r for r in map(json.loads, open(a.cache, encoding="utf-8"))}
    if not a.stub:
        from src.agent.vision import describe_facts
    with open(a.cache, "a", encoding="utf-8") as out:
        for n, p in enumerate(photos, 1):
            if p.name in cache:
                continue
            if a.stub:
                dmg = label_from_path(p) == "damaged"
                facts = {"photo_usable": True, "packaging_damaged": dmg, "item_visible": False,
                         "item_damaged": False, "description": f"(stub) box {'crushed' if dmg else 'intact'}",
                         "model": "stub"}
            else:
                for wait in (10, 30, 60, 120, None):
                    try:
                        facts = describe_facts(str(p))
                        break
                    except Exception as e:  # 429 quota: wait and retry; anything else: skip the photo
                        if wait is None or "429" not in str(e):
                            print(f"  skip {p.name}: {str(e)[:100]}", file=sys.stderr)
                            facts = None
                            break
                        time.sleep(wait)
                if facts is None:
                    continue
                time.sleep(1)
            facts.update(photo=p.name, source=a.source_name, licence=a.licence)
            cache[p.name] = facts
            out.write(json.dumps(facts, ensure_ascii=False) + "\n")
            if n % 25 == 0:
                print(f"  described {n}/{len(photos)}")

    # 3. photo rows
    rows = []
    for i, p in enumerate(photos):
        facts = cache.get(p.name)
        if facts and facts.get("description"):
            rows += [photo_case(i, k, p.name, facts, rng) for k in range(a.combos)]
    # 3b. most public photos are intact boxes or not parcels at all (-> R6): cap them, or the model
    #     learns to ask for more evidence too often (first v3 build, 11 Nov: 39% R6)
    if a.photo_r6_ratio:
        r6 = [r for r in rows if r["target"]["clause"] == "R6"]
        other = [r for r in rows if r["target"]["clause"] != "R6"]
        keep = round(len(other) * a.photo_r6_ratio)
        rows = other + random.Random(a.seed + 3).sample(r6, min(keep, len(r6)))
        print(f"photo rows: {len(other)} non-R6 kept, R6 capped {len(r6)} -> {min(keep, len(r6))}")
    # 4. template rows: a fixed number, or so that photos are about photo_share of the total
    if a.n_templates:
        n_templates = a.n_templates
    else:
        n_templates = round(len(rows) * (1 - a.photo_share) / a.photo_share) if rows else 0
    trng = random.Random(a.seed + 1)
    if a.templates == "v4":
        from src.agent.templates_v4 import eval_photo_texts, too_close
        eval_texts = [t for p in a.eval_csv if Path(p).exists() for t in eval_photo_texts(p)]
        redrawn = 0
        for i in range(n_templates):
            case = gc.make_case(i, trng, templates="v4")
            while too_close(case.damage_description, eval_texts):
                redrawn += 1
                case = gc.make_case(i, trng, templates="v4")
            rows.append({**to_example(case), "origin": "synthetic-template-v4"})
        print(f"v4 templates: {n_templates} rows, {redrawn} redrawn for being too close to an eval photo description")
    else:
        rows += [to_example(gc.make_case(i, trng)) for i in range(n_templates)]
    for r in rows:
        r.setdefault("origin", "synthetic-template")
    random.Random(a.seed + 2).shuffle(rows)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} rows -> {a.out}: {Counter(r['origin'] for r in rows)}")
    print("clauses:", dict(Counter(r["target"]["clause"] for r in rows)))
    print("photo damage types:", dict(Counter(r["damage_type"] for r in rows if r["origin"] == "photo-gemini")))


if __name__ == "__main__":
    main()
