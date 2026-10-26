---
status: accepted
---

# Facts stay full-refresh tables; no incremental models

The roadmap carried "incremental dbt models" as deferred work. Measured against the project's own job history (`INFORMATION_SCHEMA.JOBS_BY_PROJECT`, 2026-06-22 build), a full `dbt build` bills 0.438 GB, of which the two facts are 0.106 GB and 0.103 GB. BigQuery's free tier is 1 TiB of queries per month, so a daily full rebuild would use about 13 GB a month, 1.3% of the free allowance, and an incremental strategy could save at most 0.2 GB per run. The source is one static historical file: no new readings ever arrive, so there is nothing to increment. And on the sandbox the MERGE that dbt-bigquery's `merge` and `insert_overwrite` strategies execute is DML, which the sandbox rejects.

**Decision:** keep `+materialized: table` for the marts. Do not build incremental models.

**Revisit when** a real feed of new readings exists, or monthly bytes billed approach the free tier. Both would show up in the same job-history query.
