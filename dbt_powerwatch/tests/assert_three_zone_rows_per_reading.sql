-- The unpivot turns every complete reading into exactly three zone-energy rows, one per zone,
-- so the zone fact must hold three times the rows of the household fact.
-- A row comes back (and the test fails) when it does not.

with household as (select count(*) as n from {{ ref('fct_household_load') }}),
     zone      as (select count(*) as n from {{ ref('fct_zone_energy') }})

select household.n as household_rows, zone.n as zone_rows
from household cross join zone
where zone.n != 3 * household.n
