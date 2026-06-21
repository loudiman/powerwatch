# PowerWatch Roadmap

Tracked against the GSD two-day-timebox scoping: **T0 spine → T1 demoable → T2 stretch.**
Apply ruthless cutting to scope/polish — never to the schema's defensibility or the README's honesty.

**Cannot cut (the load-bearing parts):**
- The unpivot → `fct_zone_energy` + `dim_zone` (proves dimensional modeling).
- README accuracy — if a feature isn't built, it isn't in the README.
- Being able to run it live and explain *grain*, *conformed dimensions*, and the *unpivot*.

---

## Tier 0 — The spine
*Defensible the moment `dbt build` is green.*

- [x] Scaffold ELT code — loader, `stg_power`, `dim_date` / `dim_time` / `fct_household_load` / `fct_zone_energy` (unpivot), `dim_zone` seed
- [ ] Load the full ~2M-row UCI CSV into BigQuery (`download_data.py` → `load_to_bigquery.py`)
- [ ] `dbt deps` + `dbt build` → green (models + tests pass)

## Tier 1 — Make it demoable
*Shippable — you can apply with it right here.*

- [x] Add 4 dbt tests — `unique`/`not_null` on the dim keys + one `relationships` test *(definitions written; pass once `dbt build` runs)*
- [ ] Connect Looker Studio to BigQuery
- [ ] Build 3 charts — household load over time · energy-by-zone bar · hour-of-day peak heatmap *(three, not ten)*
- [ ] Screenshot charts to `docs/`
- [ ] Fill README placeholders (Looker link + screenshots); move dashboard into *What's Built*
- [ ] Push to GitHub

## Tier 2 — Stretch
*First thing to cut if time runs short.*

- [ ] Vertex AI NL-to-SQL assistant — dumbest version (schema in prompt, one Gemini call, run SQL). Keep in README only if it runs.

---

## Setup blockers

- [ ] Create `.env.example` manually (agent hook blocks writing `.env*` files)

## Deferred (deliberate tech debt)

Conscious cuts — *not* bugs. Revisit only if the project outgrows the PoC:
- Incremental dbt models (currently full `table` rebuild every run)
- Scheduled orchestration — Cloud Composer / Airflow (currently `dbt build` by hand)
- `?` missing values dropped, not imputed (one `where` filter in staging)
- Row-level access controls on the warehouse
