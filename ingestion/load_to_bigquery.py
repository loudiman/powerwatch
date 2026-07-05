"""Extract + Load: land the raw UCI CSV into a BigQuery table.

GSD scope: the dumbest thing that works. Full ~2M-row load in one shot, table
replace each run. Everything lands as STRING: the UCI missing rows mix `?` and
empty values (sub_metering_3 is blank, not `?`), and BigQuery rejects an empty
value for a numeric column. So we load raw text and let dbt staging SAFE_CAST
`?`/'' to NULL, parse the timestamp, and drop missing rows — not here.
"""
import os

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ.get("BQ_DATASET", "powerwatch")
RAW_TABLE = os.environ.get("BQ_RAW_TABLE", "raw_power")
DATA_PATH = os.environ.get("LOCAL_DATA_PATH", "household_power_consumption.txt")
LOCATION = os.environ.get("GCP_REGION", "US")  # must match the dbt profile's location

# Columns map positionally to the CSV header:
# Date;Time;Global_active_power;Global_reactive_power;Voltage;Global_intensity;
# Sub_metering_1;Sub_metering_2;Sub_metering_3
# All STRING — dbt staging SAFE_CASTs the measures so '?' and '' both become NULL.
SCHEMA = [
    bigquery.SchemaField("reading_date", "STRING"),   # D/M/YYYY, parsed in staging
    bigquery.SchemaField("reading_time", "STRING"),   # HH:MM:SS, parsed in staging
    bigquery.SchemaField("global_active_power", "STRING"),
    bigquery.SchemaField("global_reactive_power", "STRING"),
    bigquery.SchemaField("voltage", "STRING"),
    bigquery.SchemaField("global_intensity", "STRING"),
    bigquery.SchemaField("sub_metering_1", "STRING"),
    bigquery.SchemaField("sub_metering_2", "STRING"),
    bigquery.SchemaField("sub_metering_3", "STRING"),
]


def main() -> None:
    client = bigquery.Client(project=PROJECT)
    dataset = bigquery.Dataset(f"{PROJECT}.{DATASET}")
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)
    table_id = f"{PROJECT}.{DATASET}.{RAW_TABLE}"

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        skip_leading_rows=1,
        field_delimiter=";",
        # No null_marker: missing rows mix '?' and '' (empty). Staging SAFE_CASTs both.
        source_format=bigquery.SourceFormat.CSV,
        write_disposition="WRITE_TRUNCATE",
    )

    print(f"Loading {DATA_PATH} -> {table_id} ({LOCATION}) ...")
    with open(DATA_PATH, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)
    job.result()

    table = client.get_table(table_id)
    print(f"Loaded {table.num_rows:,} rows into {table_id}")


if __name__ == "__main__":
    main()
