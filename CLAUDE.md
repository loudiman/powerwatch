# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**Built and live.** ELT pipeline, dbt galaxy schema, Looker Studio dashboard and Vertex NL→SQL assistant are all shipped (PRs #1–#4). Since 2026-10 the warehouse is under data contracts and a weekly scheduled rebuild (see `docs/postmortem-2026-10.md`: the demo once expired silently for 62 days because the project runs on the BigQuery **sandbox**, where every table dies 60 days after it is built).

Commands (from the repo root, with `.venv` active and `.env` exported via `set -a; source .env; set +a`):

```bash
python -m pytest -q                               # all contracts: raw-file (DuckDB), loader, golden answers (BigQuery)
ALLOW_SANDBOX=1 python ingestion/load_to_bigquery.py   # reload; without ALLOW_SANDBOX=1 it refuses on the sandbox
cd dbt_powerwatch && dbt build && dbt source freshness  # models + unit test + data tests, then freshness
```

Decisions live in `docs/adr/`. Vocabulary lives in `GLOSSARY.md`. Billing on the GCP project is off (sandbox): no DML, 60-day expiry, so incremental models are out (ADR-0002) until billing is on (ADR-0001).

## Source dataset

`household_power_consumption.txt` (~133 MB, 2,075,259 rows) — UCI "Individual Household Electric Power Consumption", one row per **minute**, 16/12/2006 → 26/11/2010. Also present zipped (`individual+household+electric+power+consumption.zip`).

Format quirks that ingestion code must handle:
- `;`-delimited, header row present.
- Missing values: 25,979 rows (~1.25%). The first six measures are the literal `?`, **but `sub_metering_3` is empty (`''`), not `?`**. BigQuery rejects an empty value for a numeric column when a null_marker is set, so the loader lands **all columns as STRING** (no null_marker) and dbt staging `SAFE_CAST`s — turning both `?` and `''` → NULL, then one `WHERE` drops them. Don't "fix" the loader back to typed columns + null_marker; it re-breaks the load.
- `Date` is `D/M/YYYY` **non-zero-padded** (e.g. `14/1/2007`); `Time` is `HH:MM:SS`.

Columns and units:
| Column | Meaning |
| --- | --- |
| `Global_active_power` | household active power, kW |
| `Global_reactive_power` | household reactive power, kW |
| `Voltage` | V |
| `Global_intensity` | current, A |
| `Sub_metering_1` | kitchen, Wh/min |
| `Sub_metering_2` | laundry room, Wh/min |
| `Sub_metering_3` | electric water-heater + AC, Wh/min |

**Do not commit the data files** (`.txt`/`.zip`, ~150 MB total) — they are inputs, not source. Keep them out of git.

## Architecture (target)

Three stages, see `orca-paste-*457828*.png` (pipeline) and `orca-paste-*522370*.png` (dimensional model):

1. **Extract + Load** — Python ingestion reads the CSV and lands it as a BigQuery raw table (typed, `?`→null, parsed timestamp).
2. **Transform (dbt)** — `staging → marts` models build the star schema in BigQuery.
3. **Serve** — Looker Studio dashboard + Vertex AI NL→SQL over the marts.

## Dimensional model (galaxy schema)

Two fact tables sharing conformed `dim_date` / `dim_time`:

- `dim_date` (`date_key` PK) — full_date, day/month/year, quarter, day_of_week, season.
- `dim_time` (`time_key` PK) — hour, minute, time_of_day (Morning/…), is_peak_hour.
- `dim_zone` (`zone_key` PK) — zone_name, appliances.
- `fct_household_load` (grain = date+time) — active_power, reactive_power, voltage, intensity. Maps directly from the four `Global_*` columns.
- `fct_zone_energy` (grain = date+time+zone) — energy_wh. Built by **unpivoting** `Sub_metering_1/2/3` into one row per zone, joined to `dim_zone` (1=kitchen, 2=laundry, 3=water-heater/AC).

The key transform insight: the wide raw row fans out into two facts — the `Global_*` measures stay wide in `fct_household_load`, while the three sub-meters are melted long into `fct_zone_energy`.
