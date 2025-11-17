import os

from dagster import (
    Definitions,
    EnvVar,
    ScheduleDefinition,
    define_asset_job,
)
from dagster_gcp import BigQueryResource

from .defs.assets import (
    embedding_model,
    master_text_embeddings,
    daily_to_bigquery,
    master_daily_embeddings_merge,
    master_archive,
    master_daily_merge,
    master_to_bigquery,
    scrape_boletin_and_archive,
)
from .gcs_bucket_resource import GCSBucketResource
from .infoleg_scraper import InfolegClient

resource_defs = {
    "dev": {
        "ileg_client": InfolegClient(),
        "gcs": GCSBucketResource(
            project=EnvVar("GCP_PROJECT_ID"),
            bucket_name="ragboletin-data-dev",
        ),
        "bigquery": BigQueryResource(
            project=EnvVar("GCP_PROJECT_ID"),
        ),
    },
    "staging": {
        "ileg_client": InfolegClient(),
        "gcs": GCSBucketResource(
            project=EnvVar("GCP_PROJECT_ID"),
            bucket_name="ragboletin-data-stage",
        ),
        "bigquery": BigQueryResource(
            project=EnvVar("GCP_PROJECT_ID"),
        ),
    },
    "production": {
        "ileg_client": InfolegClient(),
        "gcs": GCSBucketResource(
            project=EnvVar("GCP_PROJECT_ID"),
            bucket_name="ragboletin-data-prod",
        ),
        "bigquery": BigQueryResource(
            project=EnvVar("GCP_PROJECT_ID"),
        ),
    },
}

deployment_name = os.getenv("DAGSTER_DEPLOYMENT", "dev")

# Define the job that runs all assets in sequence
infoleg_scraper_job = define_asset_job(
    name="infoleg_daily_scraper",
    description="Daily scraping job for Infoleg normas",
    selection=[
        scrape_boletin_and_archive,
        daily_to_bigquery,
        master_daily_embeddings_merge,
    ],
)

# Schedule to run daily at 7:10 AM
daily_schedule = ScheduleDefinition(
    job=infoleg_scraper_job,
    cron_schedule="10 7 * * 1-5",
    execution_timezone="America/Argentina/Buenos_Aires",
)

# Combine everything into Definitions
defs = Definitions(
    assets=[
        scrape_boletin_and_archive,
        master_daily_merge,
        master_archive,
        master_to_bigquery,
        daily_to_bigquery,
        embedding_model,
        master_text_embeddings,
        master_daily_embeddings_merge,
    ],
    jobs=[infoleg_scraper_job],
    schedules=[daily_schedule],
    resources=resource_defs[deployment_name],
)
