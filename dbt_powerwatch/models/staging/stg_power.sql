-- Staging: parse + clean the raw UCI rows.
-- GSD: drop the `?` missing values with a single WHERE filter. No imputation,
-- no rabbit-holing on data cleaning.

with raw as (

    select * from {{ source('raw', 'raw_power') }}

),

parsed as (

    select
        -- merge the non-zero-padded Date (D/M/YYYY) and Time (HH:MM:SS) into one timestamp
        parse_datetime('%d/%m/%Y %H:%M:%S', concat(reading_date, ' ', reading_time)) as reading_ts,

        global_active_power    as active_power,     -- kW
        global_reactive_power  as reactive_power,   -- kW
        voltage,                                     -- V
        global_intensity       as intensity,        -- A
        sub_metering_1,                              -- Wh/min, kitchen
        sub_metering_2,                              -- Wh/min, laundry
        sub_metering_3                               -- Wh/min, water-heater & AC

    from raw
    -- `?` rows load as NULL via the loader's null_marker; one filter drops them.
    where global_active_power is not null

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
