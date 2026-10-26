# Postmortem: the live demo expired silently

**Incident window:** 2026-08-21 (first tables expired) to 2026-10-26 (restored).
**Detected:** 2026-10-22, by accident, during a project-status review.
**Detection gap:** 62 days.
**Severity:** the public README linked to a dashboard that showed errors, and the assistant had no tables to query. Every "live" claim in the README was false for the whole window.

## Summary

The GCP project `powerwatch-2026ldm` has billing disabled, so it runs on the BigQuery sandbox. The sandbox gives every dataset a default table expiration of 60 days, and every table and view inherits it. The warehouse was built once on 2026-06-22 and never rebuilt. Sixty days later BigQuery deleted every table and view. Nothing read the warehouse after 2026-07-06, and nothing monitored it, so the failure produced no signal until a human ran `bq ls` on 2026-10-22 and found the dataset empty.

## Timeline (UTC)

All times come from `region-asia-southeast1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`, which retains 180 days of job history. 173 jobs ran in the project in that window, all by the project owner. No jobs ran in `region-us`.

| When | What | Source |
| --- | --- | --- |
| 2026-06-22 09:45:39 | First load of `raw_power` fails: "CSV table encountered too many errors" (typed columns rejected the missing values). | LOAD job, error_result |
| 2026-06-22 09:47:48 | `raw_power` loaded successfully as all-STRING columns. | LOAD job `bqjob_r501b5f2de61031e6_0000019eeeba487b_1` |
| 2026-06-22 13:42:19 to 13:42:32 | Full dbt build: `stg_power` (view), `dim_date`, `dim_time`, `fct_household_load`, `fct_zone_energy`, `dim_zone` seed. 13 jobs, 0.438 GB billed. | QUERY jobs with dbt query comments |
| 2026-06-23 | First 3 Looker Studio queries (dashboard connected). | labels `requestor=looker_studio` |
| 2026-07-02 03:47 and 04:35:59 | `rpt_household_load` and `rpt_zone_energy` views created (two 2-model dbt runs). | CREATE_VIEW jobs; `target/run_results.json` in the old clone |
| 2026-07-02 and 2026-07-05 | 28 and 114 Looker Studio queries (dashboard build-out). Last Looker query 2026-07-05 16:52:19. | labels `looker_studio_report_id=a2b135b9-…` |
| 2026-07-06 15:47 to 16:18 | 3 assistant queries (the three README examples). **Last job of any kind in the project.** | QUERY jobs |
| 2026-08-21 (computed) | `raw_power`, `stg_power`, `dim_zone`, `dim_date`, `dim_time`, `fct_household_load`, `fct_zone_energy` expired: creation time plus 60 days. | dataset `defaultTableExpirationMs = 5184000000` |
| 2026-08-31 (computed) | `rpt_household_load`, `rpt_zone_energy` expired. | same |
| 2026-07-06 to 2026-10-22 | Zero jobs. Nobody opened the dashboard, nobody ran the assistant, nothing polled the warehouse. | JOBS_BY_PROJECT |
| 2026-10-22 | `bq ls powerwatch` returns no tables. Incident recognised. | this review |

The expiry dates are computed, not observed. The exact `TABLE_EXPIRED` audit events exist in Cloud Audit Logs (Admin Activity logs are retained 400 days), but the Cloud Logging API is disabled on the project, so they cannot be read until it is enabled.

**The first query that failed against a missing table:** there is none. The only "Not found: Table" error in 180 days is from 2026-06-22 09:45:46, seven seconds after the first failed load and before the first successful one. After 2026-07-06 no query ran at all.

## Root cause

The project is on the BigQuery sandbox. Google's sandbox page states: tables, views, and partitions "automatically expire after 60 days", and the sandbox "does not support" DML statements, streaming, or the Data Transfer Service. The loader created the dataset without setting an expiration, so it inherited the sandbox default, and every object built afterwards inherited it from the dataset. Nothing rebuilt the warehouse inside 60 days.

## Contributing causes

1. **The constraint was invisible.** The 60-day expiry appeared nowhere in code, README, roadmap, or dbt config. The README said the sandbox "is enough for the pipeline". It is enough to build once. It is not enough to stay built.
2. **No consumer.** After the README screenshots were taken on 2026-07-06, nothing queried the warehouse. A dead warehouse with no readers raises no errors.
3. **No monitor.** There was no scheduled build, no `dbt source freshness`, no canary query, no uptime check. Detection depended on a human noticing.
4. **Views expire too.** The reporting views the dashboard reads carried the same 60-day expiry as the tables. Even a surviving view would have failed, since its base tables were gone ten days earlier.
5. **One-laptop reproducibility.** The credentials, dbt profile, and raw data lived in one gitignored clone. A rebuild needed that laptop and a person at it.

## Detection gap

62 days from first expiry to detection, and the detection was incidental. The gap would have been unbounded without the review. The only reason the project owner found out is that they asked "what is next for this project" and the answer required checking the warehouse.

## Impact

- The public dashboard link in the README showed a data-source error for 62 days.
- The assistant could not answer anything.
- No data was lost: the raw file, the loader, and the dbt project are all intact, and a full rebuild bills 0.44 GB.

## What went well

- The job history and the dbt artifacts reconstructed the timeline to the second without guesswork.
- The warehouse is fully derived from a 133 MB file in the repo's inputs, so restore is a rebuild, not a recovery.

## Corrective actions

| Action | Closes | Where |
| --- | --- | --- |
| Data contracts: DuckDB profile of the raw file, dbt tests on grain, row ratio, physics, freshness, a unit test on the unpivot, golden answers for the assistant. | "works" was never defined | `tests/`, `dbt_powerwatch/tests/`, `dbt_powerwatch/models/` |
| Loader stamps `_loaded_at` on every raw row; dbt source freshness runs on it. | no freshness signal | `ingestion/load_to_bigquery.py`, `_staging.yml` |
| Loader preflight reads the dataset's default expiry, sets it explicitly, prints the expiry date, and refuses to run silently on a sandbox. | invisible constraint | `ingestion/load_to_bigquery.py` |
| Scheduled GitHub Actions rebuild from a fresh clone, keyless via Workload Identity Federation, running every check. Failure is the alert. It also keeps the sandbox clock reset. | no monitor, no consumer, one-laptop rebuild | `.github/workflows/` |
| ADR on sandbox versus billing; ADR on incremental models, decided from measured bytes. | decisions undocumented | `docs/adr/` |
| README states the sandbox constraint and links this postmortem. | README honesty | `README.md` |

## Measurements kept for the ADRs

| Item | Bytes billed |
| --- | --- |
| Full dbt build, 2026-06-22 (13 jobs) | 0.438 GB |
| `fct_household_load` build | 0.106 GB |
| `fct_zone_energy` build | 0.103 GB |
| `dim_date`, `dim_time` build | 0.059 GB each |
| Median Looker Studio query | 0.049 GB |
| 145 Looker Studio queries over 3 days of dashboard building | 9.98 GB |
| One assistant question | 0.034 to 0.099 GB |
| Everything, 180 days | 10.73 GB |

BigQuery's free tier is 1 TiB of queries and 10 GiB of storage per month, with no end date, and it requires a billing account.

## Open items

- Enable the Cloud Logging API to read the exact `TABLE_EXPIRED` events: `gcloud services enable logging.googleapis.com --project=powerwatch-2026ldm`. Owner's call, since it is a project configuration change. Free.

## Evidence

Job history query:

```sql
SELECT creation_time, job_id, job_type, statement_type, state,
       total_bytes_billed, destination_table.table_id, error_result.message,
       ARRAY_TO_STRING(ARRAY(SELECT CONCAT(l.key,'=',l.value) FROM UNNEST(labels) l), ',') AS labels,
       SUBSTR(query, 1, 160) AS q
FROM `region-asia-southeast1`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
ORDER BY creation_time
```

Dataset metadata on 2026-10-22: `location = asia-southeast1`, `defaultTableExpirationMs = 5184000000` (60 days), `defaultPartitionExpirationMs = 5184000000`. Billing: `gcloud billing projects describe powerwatch-2026ldm` reports `billingEnabled: False`.
