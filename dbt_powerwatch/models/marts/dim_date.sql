-- Conformed date dimension, built from the dates actually present in the data.
-- GSD: only the columns the charts use. Add quarter/etc. when a chart needs it.

with d as (

    select distinct date_key from {{ ref('stg_power') }}

),

calc as (

    select
        date_key,
        parse_date('%Y%m%d', cast(date_key as string)) as full_date
    from d

)

select
    date_key,
    full_date,
    extract(year  from full_date) as year,
    extract(month from full_date) as month,
    extract(day   from full_date) as day,
    format_date('%A', full_date)  as day_of_week,
    case
        when extract(month from full_date) in (12, 1, 2) then 'Winter'
        when extract(month from full_date) in (3, 4, 5)  then 'Spring'
        when extract(month from full_date) in (6, 7, 8)  then 'Summer'
        else 'Autumn'
    end as season
from calc
