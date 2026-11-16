"""Step 1 of the agent: Gemini looks at the photo and describes the damage (facts only, no decision).

Usage:
  uv run python -m src.agent.vision path/to/photo.jpg          # free-text description
  uv run python -m src.agent.vision path/to/photo.jpg --json   # structured facts (used by the photo test)
Needs: gcloud auth application-default login, and GCP_PROJECT_ID in .env. Uses Vertex AI.
"""
import json
import mimetypes
import os
import sys

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")  # 2.5 Flash retired on Vertex AI, 20 Oct 2026
# v0 (7 Nov 2026): "open" counted as damaged packaging. v1: an opened intact box is not damaged.
# Change log and the evidence for it: evals/CHANGELOG.md
PROMPT_VERSION = "v1"
DAMAGE_TYPES = ["content_damaged", "packaging_only", "no_visible_damage", "unclear_photo"]

PROMPT = (
    "You inspect photos of parcels for a shipping-label platform. Describe only what you see, in one or "
    "two sentences: the state of the outer packaging, and the state of the item if it is visible. "
    "Say explicitly if the photo is too dark, blurry or does not show the item. "
    "Do not decide on a refund and do not guess anything you cannot see."
)

PROMPT_JSON = PROMPT + (
    " Answer in JSON with exactly these keys: "
    '"photo_usable" (false if too dark, blurry or not a parcel), '
    '"packaging_damaged" (true if the box, envelope or wrapping is dented, crushed, torn or wet; '
    'a box that is open but otherwise intact is NOT damaged, because merchants open parcels before claiming), '
    '"item_visible" (true if the item inside can be seen), '
    '"item_damaged" (true only if the item is visible and damaged; false otherwise), '
    '"description" (the one or two sentences).'
)


def _model():
    import vertexai
    from vertexai.generative_models import GenerativeModel

    project = os.getenv("GCP_PROJECT_ID") or os.environ["GOOGLE_CLOUD_PROJECT"]
    # 3.8 Flash runs on global, eu or us only; eu keeps photos in the EU.
    vertexai.init(project=project, location=os.getenv("GEMINI_LOCATION", "eu"))
    return GenerativeModel(MODEL)


def _image(path: str):
    from vertexai.generative_models import Part

    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as f:
        return Part.from_data(f.read(), mime_type=mime)


def describe(path: str) -> str:
    """Free-text description, as the agent uses it."""
    return _model().generate_content([PROMPT, _image(path)]).text.strip()


def describe_facts(path: str) -> dict:
    """Structured facts for scoring. Temperature 0 so a rerun gives the same answer."""
    from vertexai.generative_models import GenerationConfig

    cfg = GenerationConfig(temperature=0, response_mime_type="application/json")
    out = _model().generate_content([PROMPT_JSON, _image(path)], generation_config=cfg)
    facts = json.loads(out.text)
    facts["model"] = MODEL
    facts["prompt_version"] = PROMPT_VERSION
    return facts


def damage_type_from_facts(f: dict) -> str:
    """Map Gemini's facts to the policy's damage_type, photo only (labelling guide in DATA_MODEL_CARD.md)."""
    if not f.get("photo_usable", True):
        return "unclear_photo"
    if f.get("item_visible") and f.get("item_damaged"):
        return "content_damaged"
    if f.get("packaging_damaged"):
        return "packaging_only"
    return "no_visible_damage"


if __name__ == "__main__":
    if "--json" in sys.argv:
        facts = describe_facts(sys.argv[1])
        facts["damage_type"] = damage_type_from_facts(facts)
        print(json.dumps(facts, ensure_ascii=False, indent=2))
    else:
        print(describe(sys.argv[1]))
