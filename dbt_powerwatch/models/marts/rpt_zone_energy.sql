{{ config(materialized='view') }}

-- Reporting view: per-zone energy pre-joined to zone + conformed date/time dims.
-- One row per minute PER ZONE. Looker connects HERE. Chart 2 (energy by zone),
-- and enough columns to slice zone energy by time/season too.

select
    d.full_date,
    d.year,
    d.month,
    d.day,
    d.day_of_week,
    extract(dayofweek from d.full_date) as dow_num,   -- 1=Sun .. 7=Sat, for chart ordering
    d.season,
    t.hour,
    t.time_of_day,
    t.is_peak_hour,
    z.zone_name,
    z.appliances,
    f.energy_wh          -- Wh/min
from {{ ref('fct_zone_energy') }} f
join {{ ref('dim_zone') }} z using (zone_key)
join {{ ref('dim_date') }} d using (date_key)
join {{ ref('dim_time') }} t using (time_key)
