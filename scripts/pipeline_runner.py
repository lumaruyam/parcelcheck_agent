"""Compile the pipeline and submit it to Vertex AI Pipelines.

Run from the project root (upload data/cases.jsonl to gs://<bucket>/data/ first):
    uv run python -m scripts.pipeline_runner                                   # v1: cases.jsonl, 20 test cases
    uv run python -m scripts.pipeline_runner --data-file cases_v2.jsonl --max-test-samples 100   # v2
    uv run python -m scripts.pipeline_runner --data-file cases_v4.jsonl --epochs 1 --max-test-samples 50  # v4 (model version 2)
"""
import argparse
from datetime import datetime

from google.cloud import aiplatform
from kfp import compiler

from src.constants import (
    COMPILED_PIPELINE_PATH,
    GCS_BUCKET_URI,
    PIPELINE_NAME,
    PIPELINE_ROOT,
    PROJECT_ID,
    RAW_DATA_GCS_PATH,
    REGION,
    SEED,
    TEST_SIZE,
)
from src.pipelines.model_training_pipeline import model_training_pipeline

PIPELINE_PARAMETERS = {
    "raw_data_path": RAW_DATA_GCS_PATH,
    "test_size": TEST_SIZE,
    "seed": SEED,
    "num_train_epochs": 2,     # start small, read TensorBoard, then increase
    "learning_rate": 2e-4,
    "max_test_samples": 20,     # 0 = the whole test set; e.g. 20 for a quick first run
}
RUN_NAME_PREFIX = "parcelcheck"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-file", default=None, help="file name under gs://<bucket>/data/, e.g. cases_v2.jsonl")
    ap.add_argument("--max-test-samples", type=int, default=None, help="0 = whole test split")
    ap.add_argument("--epochs", type=int, default=None, help="e.g. 1 for the small v3 retrain (~1 h on a T4)")
    a = ap.parse_args()
    if a.data_file:
        PIPELINE_PARAMETERS["raw_data_path"] = f"{GCS_BUCKET_URI}/data/{a.data_file}"
    if a.epochs is not None:
        PIPELINE_PARAMETERS["num_train_epochs"] = a.epochs
    if a.max_test_samples is not None:
        PIPELINE_PARAMETERS["max_test_samples"] = a.max_test_samples
    print("parameters:", PIPELINE_PARAMETERS)
    run_name = f"{RUN_NAME_PREFIX}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    compiler.Compiler().compile(pipeline_func=model_training_pipeline, package_path=COMPILED_PIPELINE_PATH)
    print(f"Pipeline compiled to {COMPILED_PIPELINE_PATH}")

    aiplatform.init(project=PROJECT_ID, location=REGION, staging_bucket=GCS_BUCKET_URI)
    job = aiplatform.PipelineJob(
        display_name=run_name,
        template_path=COMPILED_PIPELINE_PATH,
        pipeline_root=PIPELINE_ROOT,
        parameter_values=PIPELINE_PARAMETERS,
        enable_caching=True,
    )
    job.submit()
    print(f"Pipeline {PIPELINE_NAME} submitted. Follow the link above in the GCP console.")


if __name__ == "__main__":
    main()
