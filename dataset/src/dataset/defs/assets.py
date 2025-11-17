import os
import io
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    DailyPartitionsDefinition,
    EnvVar,
    TableColumn,
    TableSchema,
    asset,
)
from dagster_gcp import BigQueryResource
import polars as pl

from google.cloud import bigquery as bq

MASTER_FILE = "base-infoleg-normativa-nacional.csv"
MASTER_FILE_PATH = "./data/base-infoleg-normativa-nacional.csv"
boletin_schema = pl.Schema(
    {
        "id_norma": pl.Int64,
        "tipo_norma": pl.String,
        "numero_norma": pl.String,
        "clase_norma": pl.String,
        "organismo_origen": pl.String,
        "fecha_sancion": pl.Date,
        "numero_boletin": pl.String,
        "fecha_boletin": pl.Date,
        "pagina_boletin": pl.Int64,
        "titulo_resumido": pl.String,
        "titulo_sumario": pl.String,
        "texto_resumido": pl.String,
        "observaciones": pl.String,
        "texto_original": pl.String,
        "texto_actualizado": pl.String,
        "modificada_por": pl.Int64,
        "modifica_a": pl.Int64,
    }
)

daily_partitions = DailyPartitionsDefinition(
    start_date=EnvVar("SCRAPER_START_DATE").get_value("2025-10-01"),
    timezone="America/Argentina/Buenos_Aires",
    exclusions=["* * * * 6", "* * * * 7"],  # solo dias habiles
)


@asset(
    description="Scrapes new normas from Infoleg website and uploads them to GCS.",
    compute_kind="scraping",
    required_resource_keys={"ileg_client", "gcs"},
    partitions_def=daily_partitions,
    metadata={
        "dagster/column_schema": TableSchema(
            columns=[
                TableColumn("id_norma", "int", description="Unique identifier for the norma."),
                TableColumn("tipo_norma", "string", description="Type of the norma (e.g., Ley, Decreto)."),
                TableColumn("numero_norma", "string", description="Norma number."),
                TableColumn("clase_norma", "string", description="Class of the norma."),
                TableColumn("organismo_origen", "string", description="Originating organism."),
                TableColumn("fecha_sancion", "string", description="Date of sanction (YYYY-MM-DD)."),
                TableColumn("numero_boletin", "string", description="Official bulletin number."),
                TableColumn("fecha_boletin", "string", description="Date of official bulletin (YYYY-MM-DD)."),
                TableColumn("pagina_boletin", "string", description="Page number in the official bulletin."),
                TableColumn("titulo_resumido", "string", description="Summarized title."),
                TableColumn("titulo_sumario", "string", description="Summary title."),
                TableColumn("texto_resumido", "string", description="Summarized text."),
                TableColumn("observaciones", "string", description="Observations."),
                TableColumn("texto_original", "string", description="Link to the original text."),
                TableColumn("texto_actualizado", "string", description="Link to the updated text."),
                TableColumn("modificada_por", "int", description="Count of norms that modify this one."),
                TableColumn("modifica_a", "int", description="Count of norms this one modifies."),
            ]
        )
    },
)
async def scrape_boletin_and_archive(context: AssetExecutionContext):
    """
    Scrape normas from Infoleg starting after the last scraped ID.
    Returns metadata about the scrape including output file path.
    """

    date = context.partition_key
    context.log.info(f"=== Starting Scrape for {date}===")

    output_file = f"/tmp/normas_{date}.csv"

    ileg_client = context.resources.ileg_client

    scraped_count = await ileg_client.scrape_by_date(date, output_file)
    context.log.info(f"Scrape completed: {output_file}")
    if scraped_count == 0:
        raise LookupError("[No normas extracted. Response might need inspection.")

    blob_name = f"daily_scrapes/normas_{date}.csv"
    gcs_path, blob_size = context.resources.gcs.upload_file(output_file, blob_name)

    context.log.info(f"✓ Uploaded to {gcs_path}")

    context.add_output_metadata(
        {
            "dagster/partition_row_count": scraped_count,
            "dagster/uri": gcs_path,
            "file_size_mb": round(os.path.getsize(output_file) / (1024 * 1024), 2),
        }
    )


@asset(
    description="Merges daily scrape with master",
    compute_kind="local",
    deps=[scrape_boletin_and_archive],
    partitions_def=daily_partitions,
    required_resource_keys={"gcs"},
)
def master_daily_merge(context: AssetExecutionContext) -> None:
    """
    Append new data to the master CSV dataset on disk.
    Download dataset if not present.
    """
    date = context.partition_key
    output_file = f"/tmp/normas_{date}.csv"

    storage_client = context.resources.gcs

    # Read new data (skip header)
    with open(output_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        total_rows = len(lines) - 1
        new_data = "\n" + "".join(lines[1:])

    if not Path(MASTER_FILE_PATH).exists():
        context.log.warning(
            f"{MASTER_FILE_PATH} not found, looking in {os.getcwd()}, with files {os.listdir('./data')}. Downloading master dataset from GCS."
        )
        storage_client.download_file(MASTER_FILE, MASTER_FILE_PATH)

    with open(MASTER_FILE_PATH, "a", encoding="utf-8") as mf:
        mf.write(new_data)
    context.log.info(f"✓ Appended {total_rows} rows to master file")

    context.add_output_metadata(
        {
            "rows_appended": total_rows,
        }
    )


@asset(
    description="Uploads master to GCS archive",
    compute_kind="gcs",
    deps=[master_daily_merge],
    required_resource_keys={"gcs"},
)
def master_archive(context: AssetExecutionContext) -> str:
    """
    Upload the master file to GCS for archival.
    """
    context.log.info("Uploading new master to GCS")
    gcs_path, blob_size = context.resources.gcs.upload_file(MASTER_FILE_PATH, MASTER_FILE)
    if blob_size > 1:
        context.log.info(f"Uploaded new master to {gcs_path}")

    context.add_output_metadata(
        {
            "gcs_path": gcs_path,
            "blob_size_mb": round(blob_size / (1024 * 1024), 2),
        }
    )

    return gcs_path


@asset(
    description="Creates master BigQuery table",
    compute_kind="bigquery",
)
def master_to_bigquery(context: AssetExecutionContext, bigquery: BigQueryResource) -> None:
    df = (
        pl.scan_csv(
            MASTER_FILE_PATH,
            schema=boletin_schema,
            null_values=["S/N", "s/n"],
        )
        .unique(subset=["id_norma"], keep="last")
        .collect()
    )

    context.log.info(f"Deduplicated rows loaded: {len(df)} unique records by id_norma")

    dataset_name = EnvVar("BQ_DATASET_NAME").get_value("ragboletin_dev")
    table_location = f"{bigquery.project}.{dataset_name}.master"

    context.log.info(f"Uploading master dataset to {table_location}.")
    with bigquery.get_client() as client:
        with io.BytesIO() as stream:
            df.write_parquet(stream)
            stream.seek(0)
            parquet_options = bq.ParquetOptions()
            parquet_options.enable_list_inference = True

            job_config = bq.LoadJobConfig(
                source_format=bq.SourceFormat.PARQUET,
                parquet_options=parquet_options,
            )
            job = client.load_table_from_file(
                stream,
                destination=table_location,
                job_config=job_config,
            )
        job.result(timeout=1000)

    context.add_output_metadata(
        {
            "rows_loaded": len(df),
            "table_location": table_location,
            "unique_ids": df["id_norma"].n_unique(),
        }
    )


@asset(
    description="Appends daily scrape to a BigQuery staging table",
    compute_kind="bigquery",
    deps=[scrape_boletin_and_archive],
    partitions_def=daily_partitions,
)
def daily_to_bigquery(context: AssetExecutionContext, bigquery: BigQueryResource) -> None:
    date = context.partition_key
    dataset_name = EnvVar("BQ_DATASET_NAME").get_value("ragboletin_dev")
    table_location = f"{bigquery.project}.{dataset_name}.staging"
    context.log.info(f"Appending {date} dataset to {table_location}.")

    output_file = f"/tmp/normas_{date}.csv"
    df = pl.read_csv(
        output_file,
        schema=boletin_schema,
        null_values=["S/N", "s/n"],
    )

    with bigquery.get_client() as client:
        with io.BytesIO() as stream:
            df.write_parquet(stream)
            stream.seek(0)
            parquet_options = bq.ParquetOptions()
            parquet_options.enable_list_inference = True
            job = client.load_table_from_file(
                stream,
                destination=table_location,
                job_config=bq.LoadJobConfig(
                    write_disposition=bq.WriteDisposition.WRITE_APPEND,
                    source_format=bq.SourceFormat.PARQUET,
                    parquet_options=parquet_options,
                ),
            )
        job.result(timeout=1000)

    context.add_output_metadata(
        {
            "dagster/partition_row_count": len(df),
            "table_location": table_location,
            "partition_date": date,
        }
    )


@asset(
    description="Creates an embedding model in BigQuery using Vertex AI gemini-embedding-001",
    compute_kind="bigquery",
)
def embedding_model(context: AssetExecutionContext, bigquery: BigQueryResource) -> None:
    dataset_name = EnvVar("BQ_DATASET_NAME").get_value("ragboletin_dev")
    model_name = EnvVar("BQ_MODEL_NAME").get_value("gemini-embedding-001")
    region = EnvVar("BQ_REGION").get_value("us-central1")
    connection_id = EnvVar("BQ_CONNECTION_ID").get_value("vertex_connection1")

    model_location = f"{bigquery.project}.{dataset_name}.{model_name}"
    connection_path = f"projects/{bigquery.project}/locations/{region}/connections/{connection_id}"

    context.log.info(f"Creating embedding model at {model_location}")
    context.log.info(f"Using connection: {connection_path}")

    sql = f"""
    CREATE MODEL `{model_location}`
    REMOTE WITH CONNECTION `{connection_path}`
    OPTIONS (ENDPOINT = '{model_name}');
    """

    with bigquery.get_client() as client:
        context.log.info("Executing model creation query...")
        job = client.query(sql)
        job.result()
        context.log.info(f"✓ Model created successfully: {model_location}")

    context.add_output_metadata(
        {
            "model_location": model_location,
            "connection": connection_path,
            "endpoint": model_name,
        }
    )


@asset(
    description="Creates text embeddings from the master table in BigQuery using Vertex AI gemini-embedding-001",
    compute_kind="bigquery",
    deps=[master_to_bigquery],
)
def master_text_embeddings(context: AssetExecutionContext, bigquery: BigQueryResource) -> None:
    dataset_name = EnvVar("BQ_DATASET_NAME").get_value("ragboletin_dev")
    master_table_name = EnvVar("BQ_TABLE_NAME").get_value("master")
    master_embeddings_table_name = EnvVar("BQ_EMBEDDINGS_TABLE_NAME").get_value("master_embeddings")
    model_name = EnvVar("BQ_MODEL_NAME").get_value("gemini-embedding-001")
    region = EnvVar("BQ_REGION").get_value("us-central1")
    connection_id = EnvVar("BQ_CONNECTION_ID").get_value("vertex_connection1")
    output_dimensionality = EnvVar("BQ_ML_OUTPUT_DIMENSION").get_value("768")

    model_location = f"{bigquery.project}.{dataset_name}.{model_name}"
    master_table_location = f"{bigquery.project}.{dataset_name}.{master_table_name}"
    master_embeddings_table_location = f"{bigquery.project}.{dataset_name}.{master_embeddings_table_name}"
    connection_path = f"projects/{bigquery.project}/locations/{region}/connections/{connection_id}"

    context.log.info(f"Creating embeddings at {master_embeddings_table_location}")
    context.log.info(f"Using connection: {connection_path}")

    sql = f"""
    CREATE TABLE {master_embeddings_table_location} AS
    SELECT *
    FROM ML.GENERATE_EMBEDDING(
        MODEL `{model_location}`,
        (SELECT texto_resumido as content, titulo_resumido as title
        FROM {master_table_location}),
        STRUCT(TRUE AS flatten_json_output,
            'RETRIEVAL_DOCUMENT' AS task_type,
            {output_dimensionality} AS output_dimensionality)
        WHERE ARRAY_LENGTH(ml_generate_embedding_result) > 0
    );
    """

    with bigquery.get_client() as client:
        context.log.info("Executing text embedding query...")
        job = client.query(sql)
        job.result()
        context.log.info(f"✓ Embeddings table created: {master_embeddings_table_location}")

    context.add_output_metadata(
        {
            "embeddings_table_location": master_embeddings_table_location,
            "source_table": master_table_location,
            "model_used": model_location,
            "output_dimensionality": output_dimensionality,
        }
    )


@asset(
    description="Generates embeddings from the accumulated staging data and atomically MERGES them into the master table.",
    compute_kind="bigquery",
    deps=[daily_to_bigquery, master_text_embeddings],
)
def master_daily_embeddings_merge(context: AssetExecutionContext, bigquery: BigQueryResource) -> None:
    """
    1. Generates embeddings for staging data.
    2. MERGEs the results into the master_embeddings table.
    3. TRUNCATEs the staging table for cleanup.
    """
    dataset_name = EnvVar("BQ_DATASET_NAME").get_value("ragboletin_dev")
    model_name = EnvVar("BQ_MODEL_NAME").get_value("gemini-embedding-001")
    output_dimensionality = EnvVar("BQ_ML_OUTPUT_DIMENSION").get_value("768")
    staging_table_location = f"{bigquery.project}.{dataset_name}.staging"
    master_embeddings_table_name = EnvVar("BQ_EMBEDDINGS_TABLE_NAME").get_value("master_embeddings")
    master_embeddings_table_location = f"{bigquery.project}.{dataset_name}.{master_embeddings_table_name}"
    model_location = f"{bigquery.project}.{dataset_name}.{model_name}"

    context.log.info(f"Starting batch MERGE from {staging_table_location} into {master_embeddings_table_location}")

    merge_sql = f"""
    WITH GeneratedEmbeddings AS (
        SELECT *
        FROM ML.GENERATE_EMBEDDING(
            MODEL `{model_location}`,
            (SELECT id_norma, texto_resumido as content, titulo_resumido as title
            FROM `{staging_table_location}`),
            STRUCT(TRUE AS flatten_json_output,
                'RETRIEVAL_DOCUMENT' AS task_type,
                {output_dimensionality} AS output_dimensionality)
        )
        WHERE ARRAY_LENGTH(ml_generate_embedding_result) > 0
    )
    
    MERGE INTO `{master_embeddings_table_location}` AS Target
    USING GeneratedEmbeddings AS Source
    ON Target.id_norma = Source.id_norma

    WHEN MATCHED THEN
      UPDATE SET
        Target.ml_generate_embedding_result = Source.ml_generate_embedding_result,
        Target.ml_generate_embedding_statistics = Source.ml_generate_embedding_statistics,
        Target.ml_generate_embedding_status = Source.ml_generate_embedding_status,
        Target.content = Source.content,
        Target.title = Source.title

    WHEN NOT MATCHED BY TARGET THEN
      INSERT (id_norma, ml_generate_embedding_result, ml_generate_embedding_statistics, ml_generate_embedding_status, content, title)
      VALUES (Source.id_norma, Source.ml_generate_embedding_result, Source.ml_generate_embedding_statistics, Source.ml_generate_embedding_status, Source.content, Source.title);
    """

    with bigquery.get_client() as client:
        job = client.query(merge_sql)
        job.result(timeout=1000)
        rows_modified = job.num_dml_affected_rows
        context.log.info(f"MERGE successful. Rows modified: {rows_modified}.")

        # --- Cleanup: TRUNCATE the staging table ---
        truncate_sql = f"TRUNCATE TABLE `{staging_table_location}`"
        client.query(truncate_sql).result()
        context.log.info(f"Staging table `{staging_table_location}` truncated successfully.")

    context.add_output_metadata(
        {
            "rows_merged": rows_modified,
            "master_embeddings_table": master_embeddings_table_location,
            "staging_table": staging_table_location,
            "model_used": model_location,
        }
    )
