"""Check an eval set before freezing it: no photo description seen in training, and fr tags = French text.

    python -m scripts.check_eval_leak --eval evals/eval_set_v1.csv
    python -m scripts.check_eval_leak --eval evals/eval_set_v1.csv --train data/cases_v4.jsonl

Reports, per eval row:
  - LEAK exact: the photo description is word-for-word in a training file;
  - LEAK near: it shares >= --threshold of its words with a training description (default 0.8);
  - TAG: segment says fr but the photo text looks English (or the reverse).
Exit code 1 if any leak, so it can run in CI. Tag mismatches are warnings only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from src.agent.templates_v4 import _tokens

FR_WORDS = {"le", "la", "les", "est", "et", "carton", "colis", "une", "un", "du", "des", "à", "mais", "sur", "pas"}
EN_WORDS = {"the", "is", "and", "box", "parcel", "inside", "but", "on", "not", "are"}


def lang(text: str) -> str:
    t = _tokens(text)
    return "fr" if len(t & FR_WORDS) > len(t & EN_WORDS) else "en"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default="evals/eval_set_v1.csv")
    ap.add_argument("--train", nargs="*", default=sorted(str(p) for p in Path("data").glob("cases*.jsonl")))
    ap.add_argument("--threshold", type=float, default=0.8)
    a = ap.parse_args()

    import csv
    rows = list(csv.DictReader(open(a.eval, encoding="utf-8")))
    train = {}
    for p in a.train:
        for line in open(p, encoding="utf-8"):
            d = json.loads(line)["input"]["damage_description"]
            train.setdefault(d, p)
    train_tok = [(d, _tokens(d), p) for d, p in train.items()]
    print(f"{a.eval}: {len(rows)} rows · training: {len(train)} unique descriptions from {len(a.train)} files")

    leaks = tags = 0
    for r in rows:
        texts = eval_photo_texts_row(r)
        if not texts:
            continue
        text = texts[0]
        if text in train:
            leaks += 1
            print(f"  LEAK exact  {r['id']}: {text[:70]}  ({train[text]})")
        else:
            t = _tokens(text)
            for d, u, p in train_tok:
                if t | u and len(t & u) / len(t | u) >= a.threshold:
                    leaks += 1
                    print(f"  LEAK near   {r['id']}: {text[:60]}  ~  {d[:60]}  ({p})")
                    break
        seg = r.get("segment", "")
        tagged = "fr" if seg.startswith("fr") else "en" if seg.startswith("en") else None
        if tagged and tagged != lang(text):
            tags += 1
            print(f"  TAG         {r['id']}: segment {tagged} but photo text looks {lang(text)}: {text[:60]}")
    print(f"leaks: {leaks} · tag mismatches: {tags}")
    sys.exit(1 if leaks else 0)


def eval_photo_texts_row(r: dict) -> list[str]:
    m = re.search(r'Photo: "(.*?)"', r.get("input_the_agent_receives", ""))
    return [m.group(1)] if m else []


if __name__ == "__main__":
    main()
