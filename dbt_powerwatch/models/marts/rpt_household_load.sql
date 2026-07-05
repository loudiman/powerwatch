{{ config(materialized='view') }}

-- Reporting view: whole-house load pre-joined to its conformed dims.
-- One row per minute. Looker connects HERE (no in-tool joins/blends) and picks
-- fields; Looker does the aggregation. Charts 1 (load over time) & 3 (hour heatmap).

select
    d.full_date,
    d.year,
    d.month,
    d.day,
    d.day_of_week,
    extract(dayofweek from d.full_date) as dow_num,   -- 1=Sun .. 7=Sat, for chart ordering
    d.season,
    t.hour,
    t.minute,
    t.time_of_day,
    t.is_peak_hour,
    f.active_power,      -- kW
    f.reactive_power,    -- kW
    f.voltage,           -- V
    f.intensity          -- A
from {{ ref('fct_household_load') }} f
join {{ ref('dim_date') }} d using (date_key)
join {{ ref('dim_time') }} t using (time_key)
