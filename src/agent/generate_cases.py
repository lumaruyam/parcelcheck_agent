"""Generate synthetic damaged-parcel cases, labelled by the policy.

Usage:  uv run python -m src.agent.generate_cases --n 1500 --seed 42 --out data/cases.jsonl   (v1)

v2 (after evals/report_v0.md: R5 misses, wording too narrow):
    uv run python -m src.agent.generate_cases --make-variants 8          # once: Gemini rewrites each template
    uv run python -m src.agent.generate_cases --n 3000 --seed 42 --fragile-option-rate 0.45 \
        --variants data/desc_variants.json --out data/cases_v2.jsonl
--make-variants asks Gemini for K rewrites of each description template (generic wording only,
never eval rows), saved to data/desc_variants.json. --fragile-option-rate lowers how often a
fragile item has the fragile option, so R5 (fragile without option) is about twice as frequent.
Each row carries origin="synthetic-template", "synthetic-template-v2" or "synthetic-gemini".
"""
import argparse
import json
import os
import random
import sys
from dataclasses import asdict

from src.agent.policy import CLAUSES, Case, decide

ITEMS = [  # category, fragile, typical value range
    ("ceramics", True, (8, 60)), ("glassware", True, (10, 80)), ("electronics", True, (15, 400)),
    ("cosmetics", False, (5, 45)), ("clothing", False, (10, 90)), ("books", False, (6, 30)),
    ("toys", False, (8, 50)), ("shoes", False, (25, 150)),
]
DESC = {
    "content_damaged": [
        "The box is crushed on one corner and the {item} inside is visibly broken into several pieces.",
        "Tape torn open, the {item} has a deep crack across the front and pieces are loose in the box.",
        "Outer carton wet and collapsed; the {item} is bent and clearly unusable.",
        "Le carton est écrasé et le {item} à l'intérieur est cassé en deux.",
        "Large dent on the side of the parcel; the {item} shows a shattered surface.",
    ],
    "packaging_only": [
        "The cardboard box is dented on two edges but the {item} inside looks intact.",
        "Outer packaging is scuffed and slightly torn; the {item} itself shows no damage.",
        "Le carton est abîmé sur un coin, mais le {item} semble en parfait état.",
        "Box corner crushed, contents ({item}) appear undamaged in the photo.",
    ],
    "no_visible_damage": [
        "The parcel and the {item} look normal; no damage is visible in the photo.",
        "Clean box, intact tape, the {item} appears new and undamaged.",
    ],
    "unclear_photo": [
        "The photo is too dark and blurry to assess the {item} or the packaging.",
        "Only part of the box is visible; the condition of the {item} cannot be determined.",
    ],
}
ITEM_WORD = {"ceramics": "mug", "glassware": "glass vase", "electronics": "headphones",
             "cosmetics": "perfume bottle", "clothing": "jacket", "books": "book",
             "toys": "toy", "shoes": "pair of shoes"}


FRAGILE_OPTION_RATE = 0.7  # v1; v2 uses 0.45 (--fragile-option-rate)


def make_case(i, rng, desc=DESC, templates="v1"):
    """templates="v1": the 15 sentences above (data v1-v3). "v4": src/agent/templates_v4.py
    (separate EN/FR, damage that fits the item, thousands of combinations)."""
    cat, fragile, (lo, hi) = rng.choice(ITEMS)
    dtype = rng.choices(list(DESC), weights=[0.55, 0.25, 0.1, 0.1])[0]
    c = Case(
        case_id=f"S{i:05d}", cover=rng.choices(["standard", "premium"], [0.8, 0.2])[0],
        item_category=cat, fragile_item=fragile,
        fragile_option=rng.random() < (FRAGILE_OPTION_RATE if fragile else 0.1),
        padding=rng.random() < 0.8, item_value_eur=round(rng.uniform(lo, hi), 2),
        label_fee_eur=round(rng.choice([4.9, 6.5, 8.9, 12.4]), 2),
        days_since_delivery=rng.choices([rng.randint(0, 7), rng.randint(8, 30)], [0.85, 0.15])[0],
        damage_type=dtype,
        damage_description="",
    )
    if templates == "v4":
        from src.agent.templates_v4 import describe
        c.damage_description, _lang = describe(dtype, cat, rng)
    else:
        c.damage_description = rng.choice(desc[dtype]).format(item=ITEM_WORD[cat])
    return c


def model_input(c: Case) -> dict:
    """What the fine-tuned model sees: everything except the hidden damage_type."""
    d = asdict(c)
    d.pop("damage_type")
    return d


def receipt(c: Case, dec: dict) -> str:
    ev = f'Photo assessment: "{c.damage_description}"'
    if dec["decision"] == "refund":
        head = f"Refund approved: €{dec['amount_eur']:.2f}."
    elif dec["decision"] == "decline":
        head = "Refund declined."
    else:
        head = "More evidence needed before a decision."
    return (f"{head} Rule {dec['clause']}: {CLAUSES[dec['clause']]} {ev} "
            f"Delivered {c.days_since_delivery} days ago; cover {c.cover}; declared value €{c.item_value_eur:.2f}.")


def to_example(c: Case) -> dict:
    dec = decide(c)
    target = {**dec, "receipt": receipt(c, dec)}
    return {"case_id": c.case_id, "input": model_input(c), "target": target,
            "damage_type": c.damage_type, "origin": "synthetic-template"}


def make_variants(k: int, out: str = "data/desc_variants.json") -> None:
    """Ask Gemini for k rewrites of every template (same facts, {item} kept). About 13 calls in total."""
    import time

    import vertexai
    from vertexai.generative_models import GenerationConfig, GenerativeModel
    project = os.getenv("GCP_PROJECT_ID") or os.environ["GOOGLE_CLOUD_PROJECT"]
    vertexai.init(project=project, location=os.getenv("GEMINI_LOCATION", "eu"))
    g = GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    cfg = GenerationConfig(temperature=1.0, response_mime_type="application/json")
    variants = {}
    for dtype, templates in DESC.items():
        variants[dtype] = list(templates)
        for t in templates:
            lang = "French" if any(w in t for w in ("carton", "cassé", "abîmé")) else "English"
            prompt = (f"Here is a description of a parcel photo, written by a damage inspector:\n{t}\n"
                      f"Write {k} different descriptions in {lang} with exactly the same facts (same state of the box, "
                      "same state of the item, same visibility), varied wording and sentence structure, one or two "
                      "sentences each. Keep the placeholder {item} exactly once in each. "
                      'Answer as JSON: {"variants": [...]}')
            for wait in (5, 20, 60, None):
                try:
                    out_json = json.loads(g.generate_content(prompt, generation_config=cfg).text)
                    break
                except Exception as e:  # 429 quota: wait and retry
                    if wait is None or "429" not in str(e):
                        raise
                    time.sleep(wait)
            variants[dtype] += [v for v in out_json["variants"] if v.count("{item}") == 1]
            time.sleep(1)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(variants, f, ensure_ascii=False, indent=1)
    print({d: len(v) for d, v in variants.items()}, "->", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/cases.jsonl")
    ap.add_argument("--fragile-option-rate", type=float, default=0.7)
    ap.add_argument("--variants", help="data/desc_variants.json made by --make-variants")
    ap.add_argument("--make-variants", type=int, metavar="K", help="ask Gemini for K rewrites per template, then exit")
    ap.add_argument("--paraphrase-with-gemini", action="store_true", help="v1 option: one Gemini call per row (slow)")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    if a.make_variants:
        make_variants(a.make_variants)
        sys.exit(0)
    FRAGILE_OPTION_RATE = a.fragile_option_rate
    desc = json.load(open(a.variants, encoding="utf-8")) if a.variants else DESC
    rows = [to_example(make_case(i, rng, desc)) for i in range(a.n)]
    if a.variants or a.fragile_option_rate != 0.7:
        for r in rows:
            r["origin"] = "synthetic-template-v2"
    if a.paraphrase_with_gemini:
        import vertexai
        from vertexai.generative_models import GenerativeModel  # pip/uv: google-cloud-aiplatform
        vertexai.init(project=os.getenv("GCP_PROJECT_ID") or os.environ["GOOGLE_CLOUD_PROJECT"],
                      location=os.getenv("GEMINI_LOCATION", "eu"))
        g = GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
        for r in rows:
            p = ("Rewrite this description of a damaged parcel photo in different words, same facts, "
                 "one or two sentences, no new details:\n" + r["input"]["damage_description"])
            r["input"]["damage_description"] = g.generate_content(p).text.strip()
            r["origin"] = "synthetic-gemini"
    with open(a.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"{len(rows)} cases -> {a.out}")
    print("clauses:", dict(Counter(r["target"]["clause"] for r in rows)))
