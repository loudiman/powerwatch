-- Fact 2: per-zone energy. Grain = one row per minute PER ZONE.
--
-- *** THE UNPIVOT — the load-bearing piece of the whole project. ***
-- The raw file stores the three sub-meters as WIDE columns (Sub_metering_1/2/3).
-- We melt them to LONG form — one row per (minute, zone, energy_wh) — which is
-- exactly what turns three columns into the dim_zone dimension. This is the
-- piece that proves dimensional modeling; do not simplify it away.

with stg as (

    select * from {{ ref('stg_power') }}

)

select date_key, time_key, 1 as zone_key, sub_metering_1 as energy_wh from stg
union all
select date_key, time_key, 2 as zone_key, sub_metering_2 as energy_wh from stg
union all
select date_key, time_key, 3 as zone_key, sub_metering_3 as energy_wh from stg
