-- Staging: parse + clean the raw UCI rows.
-- raw_power is loaded all-STRING (the missing rows mix '?' and '' — BigQuery
-- rejects an empty value for a numeric column on load). GSD: SAFE_CAST handles
-- both, and one WHERE filter drops the ~25,979 missing rows. No imputation.

with raw as (

    select * from {{ source('raw', 'raw_power') }}

),

parsed as (

    select
        -- merge the non-zero-padded Date (D/M/YYYY) and Time (HH:MM:SS) into one timestamp
        parse_datetime('%d/%m/%Y %H:%M:%S', concat(reading_date, ' ', reading_time)) as reading_ts,

        safe_cast(global_active_power   as float64) as active_power,     -- kW
        safe_cast(global_reactive_power as float64) as reactive_power,   -- kW
        safe_cast(voltage               as float64) as voltage,          -- V
        safe_cast(global_intensity      as float64) as intensity,        -- A
        safe_cast(sub_metering_1        as float64) as sub_metering_1,    -- Wh/min, kitchen
        safe_cast(sub_metering_2        as float64) as sub_metering_2,    -- Wh/min, laundry
        safe_cast(sub_metering_3        as float64) as sub_metering_3     -- Wh/min, water-heater & AC

    from raw
    -- safe_cast turns '?' and '' both into NULL; one filter drops the missing rows.
    where safe_cast(global_active_power as float64) is not null

)

select
    cast(format_datetime('%Y%m%d', reading_ts) as int64) as date_key,   -- conformed -> dim_date
    cast(format_datetime('%H%M', reading_ts) as int64)   as time_key,    -- conformed -> dim_time
    reading_ts,
    active_power,
    reactive_power,
    voltage,
    intensity,
    sub_metering_1,
    sub_metering_2,
    sub_metering_3
from parsed
