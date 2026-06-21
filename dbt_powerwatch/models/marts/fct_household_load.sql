-- Fact 1: whole-house load. Grain = one row per minute (date_key + time_key).
-- The four Global_* measures stay WIDE here.

select
    date_key,
    time_key,
    active_power,     -- kW
    reactive_power,   -- kW
    voltage,          -- V
    intensity         -- A
from {{ ref('stg_power') }}
