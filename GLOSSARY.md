# PowerWatch

An energy-analytics warehouse: one household's minute-by-minute electricity readings, modelled as a galaxy schema and served through a dashboard and a plain-English query assistant.

## Language

**Reading**:
One minute of measurements for the household. The finest grain in the data.
_Avoid_: row, record, sample

**Grain**:
The level of detail one fact row represents: a minute (household load) or a minute per zone (zone energy).

**Household load**:
The whole-house measures taken each minute: active power, reactive power, voltage, intensity.
_Avoid_: global measures

**Zone**:
One of the three separately metered circuits: Kitchen, Laundry, Water Heater & AC.
_Avoid_: sub-meter, circuit, room

**Zone energy**:
The energy, in watt-hours, one zone drew during one minute.
_Avoid_: sub-metering value

**Unpivot**:
Turning the three wide zone columns of a reading into one zone-energy row per zone. The move that makes zone a dimension.
_Avoid_: melt

**Conformed dimension**:
A dimension both facts share (date, time), so household load and zone energy can be analysed side by side.

**Reporting view**:
A pre-joined, analysis-ready view the dashboard reads directly. One per grain.
_Avoid_: blend

**Missing reading**:
A raw reading whose measures are absent. Dropped, never imputed.

**Peak hour**:
17:00 to 20:59, the evening demand peak.

**Time of day**:
The band a minute falls in: Morning, Afternoon, Evening, Night.

**Season**:
Winter, Spring, Summer, Autumn, assigned by calendar month.

**Raw table**:
The source file landed in the warehouse as-is, before any cleaning.
_Avoid_: landing table, source table
