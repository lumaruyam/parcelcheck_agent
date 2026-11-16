"""Score Gemini's photo reading on real photos: evals/photo_set_v1.csv → photo_results_v1.csv + photo_report_v1.md.

v0 (prompt v0, 7 Nov) is frozen: evals/photo_*_v0.*. Do not rerun it with the current prompt.

  uv run python -m scripts.run_photo_eval            # calls Gemini (about 1-2 cents per 100 photos)
  uv run python -m scripts.run_photo_eval --stub     # offline dry run, guesses from the file name

Results are cached in evals/photo_results_v0.csv: a rerun only calls Gemini for new photos.
"""
import argparse
import csv
import os
import sys
import time
from collections import Counter
from datetime import date

from src.agent.vision import DAMAGE_TYPES, PROMPT_VERSION, damage_type_from_facts

RES_COLS = ["photo_id", "origin", "dataset_label", "hand_damage_type", "photo_usable", "packaging_damaged",
            "item_visible", "item_damaged", "pred_damage_type", "description", "model", "prompt_version"]


def stub_facts(path: str) -> dict:
    n = os.path.basename(path).lower()
    dark = any(w in n for w in ("dark", "blur"))
    dmg = any(w in n for w in ("damag", "crush", "dent", "broken")) and "undamag" not in n
    return {"photo_usable": not dark, "packaging_damaged": dmg, "item_visible": "item" in n,
            "item_damaged": dmg and "item" in n, "description": "(stub)", "model": "stub"}


def with_retry(fn, path, waits=(10, 30, 60, 120)):
    """Vertex AI answers 429 when the shared quota is busy: wait and try again."""
    for w in (*waits, None):
        try:
            return fn(path)
        except Exception as e:
            if w is None or "429" not in str(e):
                raise
            print(f"  429 quota busy, retrying in {w}s", file=sys.stderr)
            time.sleep(w)


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="evals/photo_set_v1.csv")
    ap.add_argument("--results", default="evals/photo_results_v1.csv")
    ap.add_argument("--report", default="evals/photo_report_v1.md")
    ap.add_argument("--stub", action="store_true")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.set, encoding="utf-8")))
    cache = {}
    if os.path.exists(a.results) and not a.stub:
        cache = {r["photo_id"]: r for r in csv.DictReader(open(a.results, encoding="utf-8"))
                 if r.get("model") not in ("", "stub", "error") and r.get("prompt_version") == PROMPT_VERSION}

    describe = stub_facts if a.stub else __import__("src.agent.vision", fromlist=["x"]).describe_facts
    results = []
    for r in rows:
        if r["photo_id"] in cache:
            res = cache[r["photo_id"]]
        else:
            try:
                f = with_retry(describe, r["file"])
                if not a.stub:
                    time.sleep(1)  # stay under the per-minute quota
            except Exception as e:  # keep going; the row is reported as an error
                print(f"{r['photo_id']}: {e}", file=sys.stderr)
                f = {"description": f"error: {e}"[:200], "model": "error"}
            res = {k: f.get(k, "") for k in ("photo_usable", "packaging_damaged", "item_visible",
                                             "item_damaged", "description", "model", "prompt_version")}
            res["pred_damage_type"] = damage_type_from_facts(f) if f.get("model") != "error" else ""
        res.update(photo_id=r["photo_id"], origin=r["origin"], dataset_label=r["dataset_label"],
                   hand_damage_type=r["hand_damage_type"])
        results.append(res)

    with open(a.results, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RES_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    def truthy(v):
        return str(v).lower() == "true"
    ok = [r for r in results if r["model"] != "error"]

    # 1. Packaging damage vs the dataset's own label (public photos)
    pub = [r for r in ok if r["dataset_label"] in ("damaged", "normal")]
    dmg = [r for r in pub if r["dataset_label"] == "damaged"]
    nor = [r for r in pub if r["dataset_label"] == "normal"]
    hit_d = sum(truthy(r["packaging_damaged"]) for r in dmg)
    hit_n = sum(not truthy(r["packaging_damaged"]) for r in nor)
    unusable = sum(not truthy(r["photo_usable"]) for r in pub)
    real = [r for r in pub if truthy(r["photo_usable"])]
    rd = [r for r in real if r["dataset_label"] == "damaged"]
    rn = [r for r in real if r["dataset_label"] == "normal"]
    rhit_d = sum(truthy(r["packaging_damaged"]) for r in rd)
    rhit_n = sum(not truthy(r["packaging_damaged"]) for r in rn)

    # 2. damage_type vs our hand label (any photo with a hand label)
    hand = [r for r in ok if r["hand_damage_type"] in DAMAGE_TYPES]
    agree = sum(r["pred_damage_type"] == r["hand_damage_type"] for r in hand)
    conf = Counter((r["hand_damage_type"], r["pred_damage_type"]) for r in hand)
    # the error that costs money: photo read as content_damaged when a person says it is not
    over = [r for r in hand if r["pred_damage_type"] == "content_damaged" and r["hand_damage_type"] != "content_damaged"]
    missed_unclear = [r for r in hand if r["hand_damage_type"] == "unclear_photo" and r["pred_damage_type"] != "unclear_photo"]

    model = next((r["model"] for r in ok), "—")
    lines = [
        f"# Photo test: Gemini on real photos ({os.path.basename(a.set)}, prompt {PROMPT_VERSION})",
        "",
        f"Run {date.today().isoformat()} · model `{model}` · prompt {PROMPT_VERSION} · {len(results)} photos "
        f"({len(pub)} public with a dataset label, {sum(r['origin'].startswith('own') for r in results)} our own) · "
        f"errors: {len(results) - len(ok)}" + (" · **STUB, not a real result**" if a.stub else ""),
        "",
        "Gemini only describes; this checks that the facts it reads from a real photo are right. "
        "The decision and the amount are checked separately (`report_v0.md`).",
        "",
        "## 1. Packaging damage vs the dataset label (public photos)",
        "",
        "| | Result |", "|---|---|",
        f"| Damaged photos seen as damaged (recall) | {pct(hit_d, len(dmg))} |",
        f"| Normal photos seen as intact | {pct(hit_n, len(nor))} |",
        f"| Overall agreement | {pct(hit_d + hit_n, len(pub))} |",
        f"| Marked unusable | {pct(unusable, len(pub))} |",
        "",
        "Usable photos only (what Gemini judged to be a real parcel photo):",
        "",
        "| | Result |", "|---|---|",
        f"| Damaged seen as damaged | {pct(rhit_d, len(rd))} |",
        f"| Intact seen as intact | {pct(rhit_n, len(rn))} |",
        "",
        "## 2. damage_type vs our hand label",
        "",
        f"Agreement: **{pct(agree, len(hand))}**. Seen as `content_damaged` when the hand label says otherwise "
        f"(the error that would pay money): **{len(over)}**. Unclear photos not flagged: **{len(missed_unclear)}**.",
        "",
        "| Hand label → predicted | Count |", "|---|---|",
        *[f"| {h} → {p} | {n} |" for (h, p), n in sorted(conf.items())],
        "",
        "## 3. Rows to look at",
        "",
        *[f"- {r['photo_id']} ({r['origin']}): hand `{r['hand_damage_type']}`, predicted `{r['pred_damage_type']}`. "
          f"“{r['description']}”" for r in over + missed_unclear],
        "",
        "## Reading it",
        "",
        "- Fill in after the run: what the numbers mean for the trust levels in `spec.md`, and what changes.",
        "- Origin of every photo is in `photo_set_v0.csv` (`real-public` with licence, or our own). No customer photos.",
    ]
    open(a.report, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:16]))
    print(f"... full report: {a.report}")


if __name__ == "__main__":
    main()
