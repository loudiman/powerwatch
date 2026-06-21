-- Conformed time-of-day dimension (time_key = HHMM). Drives the hour-of-day heatmap.

with t as (

    select distinct time_key from {{ ref('stg_power') }}

)

select
    time_key,
    div(time_key, 100) as hour,
    mod(time_key, 100) as minute,
    case
        when div(time_key, 100) between 6  and 11 then 'Morning'
        when div(time_key, 100) between 12 and 17 then 'Afternoon'
        when div(time_key, 100) between 18 and 22 then 'Evening'
        else 'Night'
    end as time_of_day,
    div(time_key, 100) between 17 and 20 as is_peak_hour   -- 17:00–20:59 evening peak
from t
