# Dashboards

Looker Studio dashboard connected to the BigQuery `powerwatch` marts.

- Live link: _TODO — paste the Looker Studio share link here once published._
- Screenshots: `screenshots/`

Planned charts (Tier 1 — three, not ten):

1. **Household load over time** — `fct_household_load.active_power` by `dim_date.full_date`.
2. **Energy by zone** — bar of `sum(fct_zone_energy.energy_wh)` grouped by `dim_zone.zone_name`.
3. **Hour-of-day peak heatmap** — `fct_household_load` keyed by `dim_time.hour` × `dim_date.day_of_week`.
