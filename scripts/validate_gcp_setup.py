"""Test that the local environment can reach GCP (Vertex AI + GCS)."""

from google.api_core import exceptions
from google.cloud import aiplatform, storage

from src.constants import BUCKET_NAME, PROJECT_ID, REGION


def check_vertex_ai(project_id: str, region: str) -> None:
    """Initialize the Vertex AI client with the project and region."""
    aiplatform.init(project=project_id, location=region)
    print(f"Vertex AI initialized (project={project_id}, location={region})")


def check_gcs_bucket(project_id: str, bucket_name: str) -> None:
    """Connect to GCS and list the bucket contents."""
    client = storage.Client(project=project_id)

    try:
        blobs = list(client.list_blobs(bucket_name, max_results=10))
    except exceptions.NotFound as error:
        raise ValueError(
            f"GCS bucket '{bucket_name}' does not exist. "
            "Check GCP_BUCKET_NAME in your .env file or create the bucket."
        ) from error
    except exceptions.Forbidden as error:
        raise ValueError(
            f"No permission to read GCS bucket '{bucket_name}'. "
            "Check your active GCP account or service account permissions."
        ) from error

    print(f"Accessed bucket '{bucket_name}' ({len(blobs)} files):")
    for blob in blobs:
        print(f"   - {blob.name}")


def main() -> None:
    print(f"Config loaded: project={PROJECT_ID}, region={REGION}, bucket={BUCKET_NAME}")
    check_vertex_ai(PROJECT_ID, REGION)
    check_gcs_bucket(PROJECT_ID, BUCKET_NAME)
    print("\nGCP setup looks good!")


if __name__ == "__main__":
    main()
