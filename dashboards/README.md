# Dashboards

Looker Studio dashboard connected to the BigQuery `powerwatch` marts through the two
pre-joined reporting views `rpt_household_load` and `rpt_zone_energy`.

- Live link: https://lookerstudio.google.com/reporting/a2b135b9-dc45-4445-bb29-be4c45cda0f4 (public, view-only)
- Screenshot: `../docs/dashboard.png`

Charts:

1. **Average load by hour** — `rpt_household_load.active_power` by `hour`.
2. **Active power over time** — `rpt_household_load.active_power` by `full_date`.
3. **Energy by zone** — `sum(rpt_zone_energy.energy_wh)` by `zone_name`.

The views it reads live on the BigQuery sandbox and expire 60 days after each build. The
weekly rebuild (`.github/workflows/rebuild.yml`) keeps them alive; if the charts show a
data-source error, the rebuild has been failing. See `../docs/postmortem-2026-10.md`.
