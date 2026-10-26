-- UCI: global_active_power*1000/60 minus the three sub-meters "represents the active energy
-- consumed every minute (in watt hour) ... by electrical equipment not measured in
-- sub-meterings 1, 2 and 3", so it cannot be negative. The sub-meters count whole watt-hour
-- pulses, so one minute may carry at most one pulse per meter that belongs to its neighbour:
-- tolerate 3 Wh at minute grain and nothing at hour grain. Joining the two facts on the
-- conformed keys also proves the unpivot kept every zone row on its own minute.
-- Each returned row is a violation.

with per_minute as (

    select
        h.date_key,
        h.time_key,
        h.active_power * 1000 / 60 - sum(z.energy_wh) as unmetered_wh
    from {{ ref('fct_household_load') }} h
    join {{ ref('fct_zone_energy') }} z using (date_key, time_key)
    group by h.date_key, h.time_key, h.active_power

)

select 'minute' as grain, format('%d %04d', date_key, time_key) as occurred_at, unmetered_wh
from per_minute
where unmetered_wh < -3

union all

select 'hour' as grain, format('%d %02d:00', date_key, hour) as occurred_at, sum(unmetered_wh)
from (select date_key, div(time_key, 100) as hour, unmetered_wh from per_minute)
group by date_key, hour
having sum(unmetered_wh) < 0
