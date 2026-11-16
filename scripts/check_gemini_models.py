"""Which Gemini models answer on Vertex AI in our project, and at which location? (free-ish: one tiny call each)

    uv run python -m scripts.check_gemini_models
    uv run python -m scripts.check_gemini_models --locations europe-west2 eu us-central1
    uv run python -m scripts.check_gemini_models --models gemini-2.5-flash gemini-2.5-flash-001 --locations europe-west2

Uses your gcloud login (no API key). Each call sends ~20 tokens, so the whole check costs < $0.001.
"""
import argparse
import os
import warnings

from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite",
          "gemini-3.5-flash-lite", "gemini-3.8-flash"]
LOCATIONS = ["eu", "europe-west2", "europe-west1", "global"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--locations", nargs="+", default=LOCATIONS)
    a = ap.parse_args()
    import vertexai
    from vertexai.generative_models import GenerationConfig, GenerativeModel

    project = os.getenv("GCP_PROJECT_ID") or os.environ["GOOGLE_CLOUD_PROJECT"]
    print(f"project {project}\n{'model':24} " + " ".join(f"{loc:14}" for loc in a.locations))
    for model in a.models:
        row = []
        for loc in a.locations:
            try:
                vertexai.init(project=project, location=loc)
                out = GenerativeModel(model).generate_content(
                    "Answer with one word: ok", generation_config=GenerationConfig(temperature=0, max_output_tokens=5))
                row.append("OK" if out.text else "empty")
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                row.append("404" if "404" in msg or "not found" in msg.lower() else
                           "429" if "429" in msg else
                           "no-loc" if "location" in msg.lower() else type(e).__name__[:12])
                if a.models != MODELS or a.locations != LOCATIONS:
                    print(f"  {model} @ {loc}: {msg[:160]}")
        print(f"{model:24} " + " ".join(f"{r:14}" for r in row))


if __name__ == "__main__":
    main()
