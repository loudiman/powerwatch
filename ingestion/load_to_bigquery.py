"""Extract + Load: land the raw UCI CSV into a BigQuery table.

Full ~2M-row load in one shot, table replaced each run. Everything lands as STRING:
the UCI missing rows mix `?` and empty values (sub_metering_3 is blank, not `?`),
and BigQuery rejects an empty value for a numeric column. So we load raw text and
let dbt staging SAFE_CAST `?`/'' to NULL, parse the timestamp, and drop missing
rows — not here.

Two things this loader does beyond the dumb load, both born of the 2026-08 expiry
incident (docs/postmortem-2026-10.md):

- every row is stamped with `_loaded_at`, so `dbt source freshness` can tell how
  old the warehouse is;
- a preflight makes the dataset's table expiry explicit. On the BigQuery sandbox
  (no billing) every table dies 60 days after it is built and BigQuery refuses any
  longer expiry, so the loader says so, prints the date, and stops unless
  ALLOW_SANDBOX=1.
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.api_core.exceptions import BadRequest, Forbidden
from google.cloud import bigquery

# Load .env from the repo root, regardless of the current working directory.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Columns map positionally to the CSV header:
# Date;Time;Global_active_power;Global_reactive_power;Voltage;Global_intensity;
# Sub_metering_1;Sub_metering_2;Sub_metering_3  (+ _loaded_at, appended by stamp_loaded_at)
# All measures STRING — dbt staging SAFE_CASTs them so '?' and '' both become NULL.
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
    bigquery.SchemaField("_loaded_at", "TIMESTAMP"),  # when this load ran (UTC)
]

MS_PER_DAY = 86_400_000


def stamp_loaded_at(src: Path, dst: Path, loaded_at: str) -> int:
    """Copy `src` to `dst` with a `_loaded_at` column appended to the header and every row.

    Returns the number of data rows written. A BigQuery load job cannot add a constant
    column, so the stamp is applied to the file on the way in.
    """
    rows = 0
    with open(src) as fin, open(dst, "w") as fout:
        fout.write(next(fin).rstrip("\n") + ";_loaded_at\n")
        for line in fin:
            fout.write(line.rstrip("\n") + f";{loaded_at}\n")
            rows += 1
    return rows


def preflight(client: bigquery.Client, dataset: bigquery.Dataset) -> bigquery.Dataset:
    """Create the dataset if needed and make its table expiry explicit.

    Off the sandbox: clear the default expiry so tables persist. On the sandbox BigQuery
    refuses anything over 60 days; then print the expiry date loudly and stop unless
    ALLOW_SANDBOX=1 is set (the scheduled rebuild sets it, knowingly).
    """
    ds = client.create_dataset(dataset, exists_ok=True)
    ms = ds.default_table_expiration_ms
    if ms is None:
        print(f"Dataset {ds.full_dataset_id}: no default table expiry (tables persist).")
        return ds

    ds.default_table_expiration_ms = None
    ds.default_partition_expiration_ms = None
    try:
        ds = client.update_dataset(ds, ["default_table_expiration_ms", "default_partition_expiration_ms"])
        print(f"Dataset {ds.full_dataset_id}: cleared the {ms / MS_PER_DAY:.0f}-day default table expiry.")
        return ds
    except (BadRequest, Forbidden) as e:  # the sandbox answers 403: "must be less than 60 days"
        expires = datetime.now(timezone.utc) + timedelta(milliseconds=ms)
        allowed = os.environ.get("ALLOW_SANDBOX") == "1"
        print(
            f"SANDBOX: dataset {dataset.project}.{dataset.dataset_id} keeps a {ms / MS_PER_DAY:.0f}-day "
            f"default table expiry and BigQuery refused to clear it:\n    {e.message}\n"
            f"Everything loaded now expires on {expires:%Y-%m-%d}. Rebuild before then or enable billing.\n"
            + ("ALLOW_SANDBOX=1 is set: proceeding." if allowed else "Set ALLOW_SANDBOX=1 to proceed anyway."),
            file=sys.stderr,
        )
        if not allowed:
            raise SystemExit(2)
        return client.get_dataset(dataset.reference)


def main() -> None:
    project = os.environ["GCP_PROJECT_ID"]
    dataset_id = os.environ.get("BQ_DATASET", "powerwatch")
    raw_table = os.environ.get("BQ_RAW_TABLE", "raw_power")
    data_path = Path(os.environ.get("LOCAL_DATA_PATH", "household_power_consumption.txt"))
    location = os.environ.get("GCP_REGION", "US")  # must match the dbt profile's location

    client = bigquery.Client(project=project)
    dataset = bigquery.Dataset(f"{project}.{dataset_id}")
    dataset.location = location
    preflight(client, dataset)
    table_id = f"{project}.{dataset_id}.{raw_table}"

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        skip_leading_rows=1,
        field_delimiter=";",
        # No null_marker: missing rows mix '?' and '' (empty). Staging SAFE_CASTs both.
        source_format=bigquery.SourceFormat.CSV,
        write_disposition="WRITE_TRUNCATE",
    )

    loaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with tempfile.TemporaryDirectory() as tmp:
        stamped = Path(tmp) / data_path.name
        rows = stamp_loaded_at(data_path, stamped, loaded_at)
        print(f"Loading {data_path} ({rows:,} rows, _loaded_at={loaded_at}) -> {table_id} ({location}) ...")
        with open(stamped, "rb") as f:
            job = client.load_table_from_file(f, table_id, job_config=job_config)
        job.result()

    table = client.get_table(table_id)
    print(f"Loaded {table.num_rows:,} rows into {table_id}")
    if table.num_rows != rows:
        raise SystemExit(f"Row count mismatch: file has {rows:,} rows, table has {table.num_rows:,}.")
    if table.expires:
        print(f"NOTE: {table_id} expires on {table.expires:%Y-%m-%d} (sandbox).")


if __name__ == "__main__":
    main()
