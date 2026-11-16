"""Upload src/handler.py next to a fine-tuned model in GCS, then register the model
in the Vertex AI Model Registry (served by the Hugging Face pre-built container).

Run from the project root, e.g.:
    uv run python -m scripts.register_model_with_custom_handler \
        --model-uri gs://<bucket>/pipeline_root/<...>/fine-tune_<id>/model

    # a new version of an existing model:
    uv run python -m scripts.register_model_with_custom_handler \
        --model-uri gs://... --parent-model <model resource name or id>
"""

import argparse
from pathlib import Path

from google.cloud import aiplatform, storage

from src.constants import (
    MODEL_DISPLAY_NAME,
    PROJECT_ID,
    REGION,
    SERVING_CONTAINER_IMAGE_URI,
)

HANDLER_PATH = Path(__file__).resolve().parents[1] / "src" / "handler.py"


def split_gcs_uri(uri: str) -> tuple[str, str]:
    """'gs://bucket/a/b/' -> ('bucket', 'a/b')."""
    bucket_name, _, prefix = uri.removeprefix("gs://").partition("/")
    return bucket_name, prefix.strip("/")


def upload_handler(model_uri: str, handler_path: Path = HANDLER_PATH) -> str:
    """Copy handler.py to the root of the model artifacts folder; return its gs:// URI."""
    bucket_name, prefix = split_gcs_uri(model_uri)
    blob_name = f"{prefix}/handler.py" if prefix else "handler.py"
    storage.Client(project=PROJECT_ID).bucket(bucket_name).blob(blob_name).upload_from_filename(
        str(handler_path)
    )
    uri = f"gs://{bucket_name}/{blob_name}"
    print(f"Uploaded {handler_path.name} to {uri}")
    return uri


def register_model(
    model_uri: str,
    display_name: str = MODEL_DISPLAY_NAME,
    parent_model: str | None = None,
    description: str | None = None,
) -> aiplatform.Model:
    """Register the artifacts folder as a model (or a new version of parent_model)."""
    aiplatform.init(project=PROJECT_ID, location=REGION)
    model = aiplatform.Model.upload(
        display_name=display_name,
        artifact_uri=model_uri.rstrip("/"),
        serving_container_image_uri=SERVING_CONTAINER_IMAGE_URI,
        serving_container_ports=[8080],  # the port the HF container listens on
        parent_model=parent_model,
        description=description or "Phi-3-mini-4k-instruct + LoRA adapters fine-tuned to apply the ParcelCheck refund policy",
    )
    print(f"Registered {model.display_name} version {model.version_id}: {model.resource_name}")
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model-uri", required=True, help="gs:// URI of the 'model' artifact of the fine-tuning step")
    parser.add_argument("--model-name", default=MODEL_DISPLAY_NAME, help="display name in the Model Registry")
    parser.add_argument("--parent-model", default=None, help="register as a new version of this model")
    parser.add_argument("--description", default=None)
    args = parser.parse_args()

    upload_handler(args.model_uri)
    register_model(args.model_uri, args.model_name, args.parent_model, args.description)


if __name__ == "__main__":
    main()
