"""Photo-description templates v4: separate English and French, damage that fits the item, many paraphrases.

Why (Luli's hand check of eval_set_v0, 11 Nov): the v1 templates have 15 sentences, the French one
fills in English nouns ("le pair of shoes") and says a jacket or shoes are "cassé en deux".
v4 builds each description from parts (box state + item state, or a whole sentence), so there are
thousands of combinations instead of 15 sentences, with:
  - French text only with French nouns, articles and gender agreement (le/la, cassé/cassée);
  - damage words that fit the material (glass shatters, a jacket tears, a book gets soaked);
  - several item words per category (mug, cup, bowl...), loose word order, short and long forms;
  - some noise: missing final period, lowercase start, one typo in about 1 row in 12.
The damage type stays fully determined by the text (no ambiguous rows), so policy.py labels stay right.
None of these sentences was written from an eval row (evals/eval_set_v0.csv); build_photo_training_data
also drops any row whose description is too close to an eval photo description (see leak_check).

    from src.agent.templates_v4 import describe
    describe("content_damaged", "ceramics", rng)            # -> (text, "en" | "fr")
"""
from __future__ import annotations

import random
import re

FR_SHARE = 0.4  # share of French descriptions

# category -> material group (decides which damage words fit)
GROUP = {"ceramics": "brittle", "glassware": "brittle", "electronics": "device", "cosmetics": "bottle",
         "clothing": "fabric", "books": "paper", "toys": "toy", "shoes": "shoes"}

ITEMS_EN = {
    "ceramics": ["mug", "cup", "bowl", "plate", "teapot"],
    "glassware": ["glass vase", "wine glass", "glass jar", "carafe"],
    "electronics": ["headphones", "phone", "tablet", "speaker", "game controller"],
    "cosmetics": ["perfume bottle", "face cream jar", "serum bottle", "nail polish"],
    "clothing": ["jacket", "sweater", "dress", "shirt", "pair of jeans"],
    "books": ["book", "notebook", "cookbook", "comic book"],
    "toys": ["toy car", "doll", "puzzle box", "plastic robot", "toy"],
    "shoes": ["pair of shoes", "sneakers", "boots", "sandals"],
}
PLURAL_EN = {"headphones", "sneakers", "boots", "sandals", "pair of jeans", "pair of shoes"}
# French: (noun with article, gender m/f, plural?)
ITEMS_FR = {
    "ceramics": [("la tasse", "f", 0), ("le bol", "m", 0), ("l'assiette", "f", 0), ("la théière", "f", 0)],
    "glassware": [("le vase en verre", "m", 0), ("le verre à vin", "m", 0), ("le bocal", "m", 0), ("la carafe", "f", 0)],
    "electronics": [("le casque audio", "m", 0), ("le téléphone", "m", 0), ("la tablette", "f", 0), ("l'enceinte", "f", 0), ("la manette", "f", 0)],
    "cosmetics": [("le flacon de parfum", "m", 0), ("le pot de crème", "m", 0), ("le sérum", "m", 0), ("le vernis", "m", 0)],
    "clothing": [("la veste", "f", 0), ("le pull", "m", 0), ("la robe", "f", 0), ("la chemise", "f", 0), ("le jean", "m", 0)],
    "books": [("le livre", "m", 0), ("le carnet", "m", 0), ("le livre de cuisine", "m", 0), ("la BD", "f", 0)],
    "toys": [("la petite voiture", "f", 0), ("la poupée", "f", 0), ("le puzzle", "m", 0), ("le robot en plastique", "m", 0), ("le jouet", "m", 0)],
    "shoes": [("les chaussures", "f", 1), ("les baskets", "f", 1), ("les bottes", "f", 1), ("les sandales", "f", 1)],
}

# ---------- English parts ({i} = item, {be} = is/are, {s} = verb ending for singular) ----------
BOX_DAMAGED_EN = [
    "The box is crushed on one corner", "Outer carton wet and collapsed", "Big dent on the side of the box",
    "Packaging ripped open along the top", "The parcel arrived squashed almost flat", "Tape split and the flaps are open",
    "Cardboard punctured on one side", "The box is caved in on top", "Corner of the parcel smashed",
    "Box soaked through and falling apart", "Parcel badly dented", "The mailer bag is torn",
]
ITEM_DAMAGED_EN = {
    "brittle": ["the {i} inside {be} broken into several pieces", "the {i} {be} cracked right across",
                "the {i} {be} shattered, shards loose in the box", "the {i} {be} chipped and has a long crack",
                "the {i} came out in two pieces", "the {i} {be} smashed"],
    "device": ["the {i} {be} cracked on the front", "the casing of the {i} {be} split open",
               "the {i} {be} bent and a part has snapped off", "the screen of the {i} {be} smashed",
               "the {i} {be} dented and a piece is missing"],
    "bottle": ["the {i} {be} broken and leaking", "the {i} {be} cracked and half of it has spilled",
               "the cap of the {i} snapped off and the contents leaked out", "the {i} {be} smashed, liquid everywhere"],
    "fabric": ["the {i} {be} torn along a seam", "the {i} {be} soaked and stained", "the {i} has a large rip on the front",
               "the {i} {be} covered in oil stains", "the {i} {be} shredded on one side"],
    "paper": ["the {i} {be} soaked and the pages are stuck together", "the cover of the {i} {be} torn off",
              "the {i} {be} crushed and the spine is broken", "the {i} {be} water-damaged and warped"],
    "toy": ["the {i} {be} snapped in two", "a part of the {i} has broken off", "the {i} {be} crushed flat",
            "the {i} {be} cracked and pieces are missing"],
    "shoes": ["the {i} {be} crushed out of shape", "the sole of the {i} has come off", "the {i} {be} soaked and muddy",
              "a heel of the {i} {be} broken off", "the {i} {be} torn at the side"],
}
BOX_SCUFFED_EN = [
    "The box is dented on two edges", "Outer packaging scuffed and slightly torn", "Box corner crushed",
    "The carton is a bit squashed", "Parcel has a small tear in the cardboard", "Box arrived wet on one side",
    "The tape is ripped and the box is dented", "Packaging crumpled",
]
ITEM_FINE_EN = [
    "the {i} inside looks intact", "the {i} itself shows no damage", "the {i} {be} fine",
    "no damage to the {i}", "the {i} appear{s} undamaged", "the {i} {be} in perfect condition",
    "the {i} survived without a scratch",
]
NO_DAMAGE_EN = [
    "The parcel and the {i} look normal; no damage is visible.", "Clean box, tape intact, the {i} appear{s} new.",
    "Nothing wrong in the photo: box in good shape and the {i} {be} undamaged.", "The {i} and its box both look perfect.",
    "Box intact, {i} intact, no marks at all.", "Everything looks fine, the {i} {be} still in its original packaging.",
]
UNCLEAR_EN = [
    "The photo is too dark to see the {i} or the box.", "Picture very blurry; the condition of the {i} cannot be judged.",
    "Only the shipping label is visible, not the {i}.", "The photo is taken from too far away to assess the {i}.",
    "Only part of the box is in frame; the {i} cannot be seen.", "Overexposed photo, the {i} and packaging are not readable.",
]
JOIN_EN = ["; ", ", and ", " and ", ". Inside, ", ", but "]

# ---------- French parts ({i} = item with article; {e} = feminine "e"; {s} = plural "s"; {ent} = est/sont) ----------
BOX_DAMAGED_FR = [
    "Le carton est écrasé sur un coin", "Le colis est arrivé trempé et affaissé", "Le carton est défoncé sur le côté",
    "L'emballage est déchiré sur le dessus", "Le colis est arrivé presque aplati", "Le scotch est arraché et les rabats sont ouverts",
    "Le carton est percé d'un côté", "Le dessus du carton est enfoncé", "Un coin du colis est complètement écrasé",
    "Le carton est trempé et tombe en morceaux", "Le colis est très cabossé", "L'enveloppe est déchirée",
]
ITEM_DAMAGED_FR = {
    "brittle": ["{i} à l'intérieur {ent} en morceaux", "{i} {ent} fêlé{e}{s} sur toute la longueur",
                "{i} {ent} brisé{e}{s}, il y a des éclats dans le carton", "{i} {ent} ébréché{e}{s} avec une grosse fissure",
                "{i} {ent} cassé{e}{s} en deux", "{i} {ent} en miettes"],
    "device": ["{i} {ent} fissuré{e}{s} sur l'avant", "la coque de {i} est fendue", "{i} {ent} tordu{e}{s} et une pièce s'est détachée",
               "l'écran de {i} est cassé", "{i} {ent} cabossé{e}{s} et il manque un morceau"],
    "bottle": ["{i} {ent} cassé{e}{s} et fuit", "{i} {ent} fêlé{e}{s} et la moitié s'est renversée",
               "le bouchon de {i} a cassé et le contenu a coulé", "{i} {ent} brisé{e}{s}, il y a du liquide partout"],
    "fabric": ["{i} {ent} déchiré{e}{s} le long d'une couture", "{i} {ent} trempé{e}{s} et taché{e}{s}",
               "{i} a un grand accroc sur le devant", "{i} {ent} couvert{e}{s} de taches d'huile", "{i} {ent} lacéré{e}{s} d'un côté"],
    "paper": ["{i} {ent} trempé{e}{s} et les pages sont collées", "la couverture de {i} est arrachée",
              "{i} {ent} écrasé{e}{s} et le dos est cassé", "{i} {ent} gondolé{e}{s} par l'eau"],
    "toy": ["{i} {ent} cassé{e}{s} en deux", "une pièce de {i} s'est cassée", "{i} {ent} complètement écrasé{e}{s}",
            "{i} {ent} fissuré{e}{s} et il manque des morceaux"],
    "shoes": ["{i} {ent} écrasé{e}{s} et déformé{e}{s}", "la semelle de {i} s'est décollée", "{i} {ent} trempé{e}{s} et pleine{s} de boue",
              "un talon de {i} est cassé", "{i} {ent} déchiré{e}{s} sur le côté"],
}
BOX_SCUFFED_FR = [
    "Le carton est abîmé sur un coin", "L'emballage est un peu déchiré", "Le colis est cabossé sur deux bords",
    "Le carton est légèrement écrasé", "Il y a une petite déchirure dans le carton", "Le colis est mouillé d'un côté",
    "Le scotch est arraché et le carton est enfoncé", "L'emballage est froissé",
]
ITEM_FINE_FR = [
    "{i} semble intact{e}{s}", "{i} n'a rien", "aucun dégât sur {i}", "{i} {ent} en parfait état",
    "{i} paraî{t} en bon état", "{i} {ent} intact{e}{s} à l'intérieur",
]
NO_DAMAGE_FR = [
    "Le colis et {i} ont l'air normaux, aucun dégât visible.", "Carton propre, scotch intact, {i} {ent} comme neu{f}.",
    "Rien d'anormal sur la photo : le carton est en bon état et {i} aussi.", "{I} et son emballage sont en parfait état.",
    "Carton intact, {i} intact{e}{s}, aucune marque.",
]
UNCLEAR_FR = [
    "La photo est trop sombre pour voir {i} ou le carton.", "Photo très floue, impossible de juger l'état de {i}.",
    "On ne voit que l'étiquette d'envoi, pas {i}.", "La photo est prise de trop loin pour évaluer {i}.",
    "Seule une partie du carton est visible, on ne voit pas {i}.", "Photo surexposée, on ne distingue ni {i} ni l'emballage.",
]
JOIN_FR = [" et ", ", ", " ; ", ", mais ", ". À l'intérieur, "]


def _fill_en(t: str, item: str) -> str:
    pl = item in PLURAL_EN
    return t.format(i=item, be="are" if pl else "is", s="" if pl else "s", I=item[:1].upper() + item[1:])


def _fill_fr(t: str, noun: str, gender: str, plural: int) -> str:
    out = t.format(i=noun, I=noun[:1].upper() + noun[1:], e="e" if gender == "f" else "", s="s" if plural else "",
                   ent="sont" if plural else "est", t="t" if not plural else "ssent",
                   f=("ve" if gender == "f" else "f") + ("s" if plural else ""))
    out = out.replace("paraîssent", "paraissent").replace("pleines", "pleines")
    # French elision: "de le" -> "du", "de les" -> "des", "de la" stays, "de l'" stays
    out = re.sub(r"\bde le\b", "du", out)
    out = re.sub(r"\bde les\b", "des", out)
    out = re.sub(r"\bà le\b", "au", out)
    return out


def _join(box: str, item: str, joins: list[str], rng: random.Random, contrast: bool) -> str:
    j = rng.choice([x for x in joins if ("but" in x or "mais" in x) == contrast] or joins)
    if j.startswith("."):  # ". Inside, " / ". À l'intérieur, ": don't say "inside" twice
        item = item.replace(" inside", "").replace(" à l'intérieur", "")
    if rng.random() < 0.2:  # item first, box second
        return item[:1].upper() + item[1:] + ("; " if joins is JOIN_EN else " ; ") + box[:1].lower() + box[1:] + "."
    return box + j + item + "."


def _noise(text: str, rng: random.Random) -> str:
    if rng.random() < 0.15:
        text = text.rstrip(".")
    if rng.random() < 0.1:
        text = text[:1].lower() + text[1:]
    if rng.random() < 0.08:  # one typo: swap two letters inside a long word
        words = text.split(" ")
        long_idx = [k for k, w in enumerate(words) if len(w) > 5 and w.isalpha()]
        if long_idx:
            k = rng.choice(long_idx)
            w = words[k]
            p = rng.randrange(1, len(w) - 2)
            words[k] = w[:p] + w[p + 1] + w[p] + w[p + 2:]
            text = " ".join(words)
    return text


def describe(damage_type: str, category: str, rng: random.Random, fr_share: float = FR_SHARE) -> tuple[str, str]:
    """One photo description for this damage type and item category. Returns (text, language)."""
    group = GROUP[category]
    if rng.random() < fr_share:
        noun, g, pl = rng.choice(ITEMS_FR[category])
        fill = lambda t: _fill_fr(t, noun, g, pl)  # noqa: E731
        if damage_type == "content_damaged":
            text = _join(rng.choice(BOX_DAMAGED_FR), fill(rng.choice(ITEM_DAMAGED_FR[group])), JOIN_FR, rng, False)
        elif damage_type == "packaging_only":
            text = _join(rng.choice(BOX_SCUFFED_FR), fill(rng.choice(ITEM_FINE_FR)), JOIN_FR, rng, True)
        elif damage_type == "no_visible_damage":
            text = fill(rng.choice(NO_DAMAGE_FR))
        else:
            text = fill(rng.choice(UNCLEAR_FR))
        lang = "fr"
    else:
        item = rng.choice(ITEMS_EN[category])
        fill = lambda t: _fill_en(t, item)  # noqa: E731
        if damage_type == "content_damaged":
            text = _join(rng.choice(BOX_DAMAGED_EN), fill(rng.choice(ITEM_DAMAGED_EN[group])), JOIN_EN, rng, False)
        elif damage_type == "packaging_only":
            text = _join(rng.choice(BOX_SCUFFED_EN), fill(rng.choice(ITEM_FINE_EN)), JOIN_EN, rng, True)
        elif damage_type == "no_visible_damage":
            text = fill(rng.choice(NO_DAMAGE_EN))
        else:
            text = fill(rng.choice(UNCLEAR_EN))
        lang = "en"
    return _noise(text, rng), lang


# ---------- leak check: is a training description too close to an eval photo description? ----------
def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-zàâçéèêëîïôûùüÿœ']+", s.lower()))


def too_close(text: str, eval_texts: list[str], threshold: float = 0.8) -> bool:
    """True if text equals an eval description or shares >= threshold of its words (Jaccard)."""
    t = _tokens(text)
    for e in eval_texts:
        u = _tokens(e)
        if t == u or (t | u and len(t & u) / len(t | u) >= threshold):
            return True
    return False


def eval_photo_texts(path: str = "evals/eval_set_v0.csv") -> list[str]:
    """Photo descriptions quoted in an eval CSV ('Photo: "..."' inside input_the_agent_receives)."""
    import csv
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        m = re.search(r'Photo: "(.*?)"', r.get("input_the_agent_receives", ""))
        if m:
            out.append(m.group(1))
    return out
