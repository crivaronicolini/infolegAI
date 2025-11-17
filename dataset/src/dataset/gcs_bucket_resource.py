from dagster import ConfigurableResource, EnvVar, Tuple
from google.cloud import storage
from google.oauth2 import service_account
import os
from typing import Optional
from pydantic import Field


class GCSBucketResource(ConfigurableResource):
    """
    A Dagster resource for managing Google Cloud Storage bucket operations.

    Example usage:
        from dagster import asset, Definitions

        @asset
        def my_asset(gcs: GCSBucketResource):
            gcs.upload_file("local_file.txt", "remote_path/file.txt")
            content = gcs.download_file("remote_path/file.txt")
            return content

        defs = Definitions(
            assets=[my_asset],
            resources={
                "gcs": GCSBucketResource(
                    project=EnvVar("GCS_PROJECT_ID"),
                    bucket_name=EnvVar("GCS_BUCKET_NAME"),
                )
            }
        )
    """

    project: str = Field(
        description="GCP project ID",
    )

    bucket_name: str = Field(
        description="GCS bucket name",
    )

    credentials_path: Optional[str] = Field(
        default=None,
        description="Path to service account credentials JSON file. If None, uses default credentials.",
    )

    def _get_client(self) -> storage.Client:
        """Initialize and return a GCS client."""
        if self.credentials_path and os.path.exists(self.credentials_path):
            credentials = service_account.Credentials.from_service_account_file(self.credentials_path)
            return storage.Client(project=self.project, credentials=credentials)
        return storage.Client(project=self.project)

    def _get_bucket(self) -> storage.Bucket:
        """Get the configured bucket."""
        client = self._get_client()
        return client.bucket(self.bucket_name)

    def upload_file(
        self,
        local_path: str,
        destination_blob_name: str,
        content_type: Optional[str] = None,
    ) -> tuple[str, Optional[int]]:
        """
        Upload a file to the GCS bucket.

        Args:
            local_path: Path to the local file
            destination_blob_name: Destination path in the bucket
            content_type: Optional content type for the blob

        Returns:
            The public URL of the uploaded file
        """
        bucket = self._get_bucket()
        blob = bucket.blob(destination_blob_name)

        if content_type:
            blob.upload_from_filename(local_path, content_type=content_type)
        else:
            blob.upload_from_filename(local_path)

        return f"gs://{self.bucket_name}/{destination_blob_name}", blob.size

    def upload_from_string(
        self, content: str, destination_blob_name: str, content_type: str = "text/plain"
    ) -> tuple[str, Optional[int]]:
        """
        Upload string content directly to the GCS bucket.

        Args:
            content: String content to upload
            destination_blob_name: Destination path in the bucket
            content_type: Content type for the blob

        Returns:
            The public URL of the uploaded file
            The size of the file
        """
        bucket = self._get_bucket()
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_string(content, content_type=content_type)

        return f"gs://{self.bucket_name}/{destination_blob_name}", blob.size

    def download_file(self, blob_name: str, local_path: Optional[str] = None) -> str:
        """
        Download a file from the GCS bucket.

        Args:
            blob_name: Name of the blob in the bucket
            local_path: Optional local path to save the file. If None, returns content as string.

        Returns:
            If local_path is provided, returns the local path. Otherwise returns the content as string.
            Raises FileNotFoundError if the requested file is not found.
        """
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)

        if not blob.exists():
            raise FileNotFoundError(f"Blob '{blob_name}' not found in bucket '{self.bucket_name}'")

        if local_path:
            blob.download_to_filename(local_path)
            return local_path
        else:
            return blob.download_as_text()

    def download_as_bytes(self, blob_name: str) -> bytes:
        """
        Download a file from the GCS bucket as bytes.

        Args:
            blob_name: Name of the blob in the bucket

        Returns:
            File content as bytes
        """
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)
        return blob.download_as_bytes()

    def delete_file(self, blob_name: str) -> None:
        """
        Delete a file from the GCS bucket.

        Args:
            blob_name: Name of the blob to delete
        """
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)
        blob.delete()

    def rename_file(self, blob_name: str, new_name: str) -> str:
        """
        Rename a file from the GCS bucket.

        Args:
            blob_name: Name of the blob to rename
        """
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)
        blob = bucket.rename_blob(blob, new_name)
        return f"gs://{self.bucket_name}/{blob.name}"

    def list_files(self, prefix: Optional[str] = None) -> list[str]:
        """
        List files in the GCS bucket.

        Args:
            prefix: Optional prefix to filter files

        Returns:
            List of blob names
        """
        bucket = self._get_bucket()
        blobs = bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]

    def file_exists(self, blob_name: str) -> bool:
        """
        Check if a file exists in the GCS bucket.

        Args:
            blob_name: Name of the blob to check

        Returns:
            True if the file exists, False otherwise
        """
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)
        return blob.exists()

    def get_public_url(self, blob_name: str) -> str:
        """
        Get the GCS URI for a blob.

        Args:
            blob_name: Name of the blob

        Returns:
            GCS URI (gs://bucket/path)
        """
        return f"gs://{self.bucket_name}/{blob_name}"


# # Example usage in a Dagster pipeline
# if __name__ == "__main__":
#     from dagster import asset, Definitions, materialize
#
#     @asset
#     def upload_example_file(gcs: GCSBucketResource):
#         """Example asset that uploads a file to GCS."""
#         # Upload from string
#         gcs_path = gcs.upload_from_string(
#             content="Hello from Dagster!", destination_blob_name="example/test.txt"
#         )
#         return gcs_path
#
#     @asset
#     def process_gcs_file(gcs: GCSBucketResource, upload_example_file: str):
#         """Example asset that downloads and processes a file from GCS."""
#         # Download the file
#         content = gcs.download_file("example/test.txt")
#
#         # Process it
#         processed_content = content.upper()
#
#         # Upload processed version
#         gcs.upload_from_string(
#             content=processed_content, destination_blob_name="example/processed.txt"
#         )
#
#         # List all files with prefix
#         files = gcs.list_files(prefix="example/")
#         return {"files": files, "content": processed_content}
#
#     defs = Definitions(
#         assets=[upload_example_file, process_gcs_file],
#         resources={
#             "gcs": GCSBucketResource(
#                 project=EnvVar("GCS_PROJECT_ID"),
#                 gcs_bucket=EnvVar("GCS_BUCKET_NAME"),
#                 # credentials_path=EnvVar("GOOGLE_APPLICATION_CREDENTIALS")  # Optional
#             )
#         },
#     )
