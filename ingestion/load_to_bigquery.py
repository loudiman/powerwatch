"""Extract + Load: land the raw UCI CSV into a BigQuery table.

GSD scope: the dumbest thing that works. Full ~2M-row load in one shot, table
replace each run. The `;` delimiter and the `?` missing-value marker are handled
by the load job; everything downstream (timestamp parsing, dropping `?` rows,
the unpivot) happens in dbt staging/marts — not here.
"""
import os

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ.get("BQ_DATASET", "powerwatch")
RAW_TABLE = os.environ.get("BQ_RAW_TABLE", "raw_power")
DATA_PATH = os.environ.get("LOCAL_DATA_PATH", "household_power_consumption.txt")

# Columns map positionally to the CSV header:
# Date;Time;Global_active_power;Global_reactive_power;Voltage;Global_intensity;
# Sub_metering_1;Sub_metering_2;Sub_metering_3
SCHEMA = [
    bigquery.SchemaField("reading_date", "STRING"),   # D/M/YYYY, parsed in staging
    bigquery.SchemaField("reading_time", "STRING"),   # HH:MM:SS, parsed in staging
    bigquery.SchemaField("global_active_power", "FLOAT64"),
    bigquery.SchemaField("global_reactive_power", "FLOAT64"),
    bigquery.SchemaField("voltage", "FLOAT64"),
    bigquery.SchemaField("global_intensity", "FLOAT64"),
    bigquery.SchemaField("sub_metering_1", "FLOAT64"),
    bigquery.SchemaField("sub_metering_2", "FLOAT64"),
    bigquery.SchemaField("sub_metering_3", "FLOAT64"),
]


def main() -> None:
    client = bigquery.Client(project=PROJECT)
    client.create_dataset(DATASET, exists_ok=True)
    table_id = f"{PROJECT}.{DATASET}.{RAW_TABLE}"

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        skip_leading_rows=1,
        field_delimiter=";",
        null_marker="?",  # UCI missing-value marker -> NULL on load
        source_format=bigquery.SourceFormat.CSV,
        write_disposition="WRITE_TRUNCATE",
    )

    print(f"Loading {DATA_PATH} -> {table_id} ...")
    with open(DATA_PATH, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)
    job.result()

    table = client.get_table(table_id)
    print(f"Loaded {table.num_rows:,} rows into {table_id}")


if __name__ == "__main__":
    main()
