# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**Greenfield.** As of this writing the repo contains only the source dataset and two design diagrams — no code, no tracked files (everything is untracked), empty `README.md`. There is no build/lint/test tooling yet; do not invent commands. When you scaffold the pipeline, update this file with the real commands.

PowerWatch is a planned **ELT pipeline** that turns the UCI household-power dataset into a BigQuery star schema, then serves it via a Looker Studio dashboard and a Vertex AI natural-language→SQL interface.

## Source dataset

`household_power_consumption.txt` (~133 MB, 2,075,259 rows) — UCI "Individual Household Electric Power Consumption", one row per **minute**, 16/12/2006 → 26/11/2010. Also present zipped (`individual+household+electric+power+consumption.zip`).

Format quirks that ingestion code must handle:
- `;`-delimited, header row present.
- Missing values are the literal `?` (whole-minute gaps, ~1.25% of rows). Parse as null, not 0.
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
