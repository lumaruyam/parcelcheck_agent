"""Every setting in one place: read from .env (course pattern), with P4 names."""
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_REGION = "europe-west2"


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise ValueError(f"{name} is not set. Add it to your .env file (see .env.example).")
    return value


def clean_bucket_name(bucket_name: str) -> str:
    return bucket_name.removeprefix("gs://").strip("/")


PROJECT_ID = get_env("GCP_PROJECT_ID", "your-project-id")
REGION = get_env("GCP_REGION", DEFAULT_REGION)
BUCKET_NAME = clean_bucket_name(os.getenv("GCP_BUCKET_NAME", "your-bucket-name"))
GCS_BUCKET_URI = f"gs://{BUCKET_NAME}"

# ---------- Session 2: data ----------
RAW_DATA_FILE = os.getenv("RAW_DATA_FILE", "cases.jsonl")  # made by src/agent/generate_cases.py; v2: cases_v2.jsonl
RAW_DATA_GCS_PATH = f"{GCS_BUCKET_URI}/data/{RAW_DATA_FILE}"
TEST_SIZE = 0.15                                      # held-out test set: never tuned on
SEED = 42

PIPELINE_NAME = "parcelcheck-phi3-refund-pipeline"
PIPELINE_ROOT = f"{GCS_BUCKET_URI}/pipeline_root"
COMPILED_PIPELINE_PATH = "model_training_pipeline.json"

# ---------- Session 4: registry, endpoint ----------
MODEL_DISPLAY_NAME = "parcelcheck-phi-3-mini"
# Hugging Face pre-built inference container (transformers 4.46 -> peft 0.13.2), course setting
SERVING_CONTAINER_IMAGE_URI = (
    "us-docker.pkg.dev/deeplearning-platform-release/gcr.io/"
    "huggingface-pytorch-inference-cu121.2-3.transformers.4-46.ubuntu2204.py311"
)
PROJECT_NUMBER = os.getenv("GCP_PROJECT_NUMBER", "")
ENDPOINT_ID = os.getenv("GCP_ENDPOINT_ID", "")
ENDPOINT_URL = (
    f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_NUMBER or PROJECT_ID}"
    f"/locations/{REGION}/endpoints/{ENDPOINT_ID}:predict"
)

# ---------- Product: override switch ----------
AUTONOMY_ENABLED = os.getenv("AUTONOMY_ENABLED", "true").lower() == "true"
