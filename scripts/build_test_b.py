"""Build the real-photo test set (test B + our own photos) as evals/photo_set_v0.csv.

Recipe: DATA_MODEL_CARD.md, "Test B build recipe". Photos stay out of git (evals/photos/ is ignored);
upload them to the bucket. Only the CSV, with source and licence on every row, is committed.

1. Download each Roboflow dataset on your Mac and unzip each into its own folder:
   - classification datasets: format "Folder Structure" (the class is the folder name);
   - detection datasets: format "YOLOv8" (the class comes from the label files + data.yaml).
2. Put the team's own photos in one folder (labels and addresses covered or blurred first).
3. Run:
   uv run --with imagehash --with pillow --with pyyaml python -m scripts.build_test_b \
       --source ~/Downloads/d3:D3-roboflow-parcel-damage-classification:"CC BY 4.0" \
       --source ~/Downloads/d4:D4-roboflow-damaged-package-detection:"CC BY 4.0" --exclude-class food \
       --exclude ~/Downloads/yolo_train_a --exclude ~/Downloads/yolo_train_b \
       --own ~/Desktop/parcel_photos
"""
import argparse
import csv
import random
import shutil
from pathlib import Path

IMG = {".jpg", ".jpeg", ".png", ".webp"}
NORMAL_WORDS = ("undamaged", "not_damaged", "not-damaged", "normal", "intact", "good", "ok")
DAMAGED_WORDS = ("damag", "broken", "crush", "dent", "torn")
COLUMNS = ["photo_id", "file", "origin", "source", "licence", "original_name", "dataset_label",
           "hand_damage_type", "hand_label_by", "notes"]


def images(folder: Path):
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMG)


SPLITS = {"train", "valid", "val", "test"}


def label_from_path(p: Path) -> str | None:
    """Folder export: the class is the image's folder. A class folder right under train/valid/test
    with no damage word in its name (e.g. "packaging boxes") counts as normal."""
    cls, split = p.parent.name.lower(), p.parent.parent.name.lower()
    if any(w in cls for w in NORMAL_WORDS):  # checked first: "undamaged" contains "damag"
        return "normal"
    if any(w in cls for w in DAMAGED_WORDS):
        return "damaged"
    if split in SPLITS:
        return "normal"
    return None


def yolo_labeller(root: Path):
    """For a YOLO export: image → damaged / normal from its label file, or None if unclear."""
    yml = next(iter(sorted(root.rglob("data.yaml"))), None)
    if yml is None:
        return None
    import yaml

    names = yaml.safe_load(open(yml, encoding="utf-8")).get("names", [])
    names = dict(enumerate(names)) if isinstance(names, list) else {int(k): v for k, v in names.items()}

    def kind(name: str):
        n = str(name).lower()
        if any(w in n for w in NORMAL_WORDS):
            return "normal"
        if any(w in n for w in DAMAGED_WORDS):
            return "damaged"
        return None

    def label(img: Path):
        parts = list(img.parts)
        if "images" not in parts:
            return None
        i = len(parts) - 1 - parts[::-1].index("images")
        txt = Path(*parts[:i], "labels", *parts[i + 1:]).with_suffix(".txt")
        if not txt.exists():
            return None
        kinds = {kind(names.get(int(line.split()[0]), "")) for line in open(txt) if line.strip()}
        if "damaged" in kinds:
            return "damaged"
        if kinds == {"normal"}:
            return "normal"
        return None  # no box, or only classes we cannot map: left out

    print(f"{root}: YOLO export, classes {names}")
    return label


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", action="append", default=[], help="DIR:NAME:LICENCE")
    ap.add_argument("--exclude", action="append", default=[], help="folders of the YOLO training data")
    ap.add_argument("--own", help="folder of the team's own photos")
    ap.add_argument("--exclude-class", action="append", default=[],
                    help="skip class folders whose name contains this text, e.g. food")
    ap.add_argument("--exclude-csv", action="append", default=[],
                    help="earlier photo set(s): their images are never sampled again (fresh test)")
    ap.add_argument("--id-prefix", default="PH", help="photo ids, e.g. PH (v0) or PB (v1)")
    ap.add_argument("--n-per-class", type=int, default=50)
    ap.add_argument("--max-hamming", type=int, default=6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default="evals/photos")
    ap.add_argument("--csv", default="evals/photo_set_v0.csv")
    a = ap.parse_args()

    import imagehash
    from PIL import Image

    def phash(p):
        with Image.open(p) as im:
            return imagehash.phash(im.convert("RGB"))

    excluded = [phash(p) for d in a.exclude for p in images(Path(d).expanduser())]
    print(f"excluded set: {len(excluded)} hashes")

    used = set()
    for prev in a.exclude_csv:
        used |= {r["original_name"] for r in csv.DictReader(open(prev, encoding="utf-8"))}
    if used:
        print(f"not sampling again: {len(used)} images from {a.exclude_csv}")


    pool = {"damaged": [], "normal": []}
    seen, skipped = [], {"no_label": 0, "excluded_class": 0, "near_yolo_train": 0, "duplicate": 0}
    classes = {}
    for spec in a.source:
        d, name, licence = spec.split(":", 2)
        root = Path(d).expanduser()
        labeller = yolo_labeller(root) or label_from_path
        for p in images(root):
            if any(x.lower() in p.parent.name.lower() for x in a.exclude_class):
                skipped["excluded_class"] += 1
                continue
            if p.name in used:
                skipped["already_used"] = skipped.get("already_used", 0) + 1
                continue
            lab = labeller(p)
            classes[(name, p.parent.name, lab)] = classes.get((name, p.parent.name, lab), 0) + 1
            if lab is None:
                skipped["no_label"] += 1
                continue
            h = phash(p)
            if any(h - e <= a.max_hamming for e in excluded):
                skipped["near_yolo_train"] += 1
                continue
            if any(h - s <= a.max_hamming for s in seen):
                skipped["duplicate"] += 1
                continue
            seen.append(h)
            pool[lab].append((p, name, licence))
    print("class folder → label (images found):")
    for (src, folder, lab), n in sorted(classes.items()):
        print(f"  {src} · {folder!r} → {lab} ({n})")
    print("kept after de-dup:", {k: len(v) for k, v in pool.items()}, "skipped:", skipped)

    rng = random.Random(a.seed)
    out = Path(a.out_dir)
    rows = []
    for lab in ("damaged", "normal"):
        for p, name, licence in rng.sample(pool[lab], min(a.n_per_class, len(pool[lab]))):
            rows.append({"origin": "real-public", "source": name, "licence": licence,
                         "original_name": p.name, "dataset_label": lab, "_path": p, "_sub": "test_b"})
    if a.own:
        for p in images(Path(a.own).expanduser()):
            rows.append({"origin": "own photo · team, labels blurred", "source": "team", "licence": "ours",
                         "original_name": p.name, "dataset_label": "", "_path": p, "_sub": "own"})
    rng.shuffle(rows)

    for i, r in enumerate(rows, 1):
        r["photo_id"] = f"{a.id_prefix}{i:03d}"
        dest = out / r.pop("_sub") / f"{r['photo_id']}{r['_path'].suffix.lower()}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(r.pop("_path"), dest)
        r["file"] = dest.as_posix()
        r.update(hand_damage_type="", hand_label_by="", notes="")

    with open(a.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["photo_id"]))
    print(f"{len(rows)} photos → {a.csv}; files in {out}/")
    print("Next: two people fill hand_damage_type independently (guide in DATA_MODEL_CARD.md), then")
    print("      gsutil -m cp -r evals/photos gs://$GCP_BUCKET_NAME/images/")


if __name__ == "__main__":
    main()
