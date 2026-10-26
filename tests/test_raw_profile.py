"""Contracts on the raw UCI file, checked with DuckDB: an engine independent of BigQuery.

Every expected value comes from outside this pipeline: the UCI dataset page
(https://archive.ics.uci.edu/dataset/235), arithmetic on the file's own first and
last timestamps, or the physics of the meters. None comes from the README.

Set POWERWATCH_RAW_PATH to run the same contract against another file.
"""
import os
from pathlib import Path

import duckdb
import pytest

RAW = Path(
    os.environ.get(
        "POWERWATCH_RAW_PATH",
        Path(__file__).resolve().parents[1] / "household_power_consumption.txt",
    )
)

UCI_COLUMNS = [
    "Date", "Time", "Global_active_power", "Global_reactive_power", "Voltage",
    "Global_intensity", "Sub_metering_1", "Sub_metering_2", "Sub_metering_3",
]
UCI_ROWS = 2_075_259            # UCI: "This archive contains 2075259 measurements"
MISSING_READINGS = 25_979       # UCI: "nearly 1,25% of the rows"; exact count from the file
COMPLETE_READINGS = UCI_ROWS - MISSING_READINGS

# Meter quantization, asserted below and then used as the physics tolerances.
INTENSITY_QUANTUM_A = 0.2       # Global_intensity only ever takes multiples of 0.2 A
PULSE_WH = 1                    # each sub-meter counts whole watt-hours


@pytest.fixture(scope="module")
def db():
    if not RAW.exists():
        pytest.skip(f"{RAW} not present; run ingestion/download_data.py")
    con = duckdb.connect()
    con.execute(
        f"create table raw as select * from read_csv('{RAW}', delim=';', header=true, all_varchar=true)"
    )
    con.execute(
        """
        create table r as
        select
            strptime(Date || ' ' || Time, '%d/%m/%Y %H:%M:%S') as ts,
            try_cast(Global_active_power   as double) as p,    -- kW
            try_cast(Global_reactive_power as double) as q,    -- kW
            try_cast(Voltage               as double) as v,    -- V
            try_cast(Global_intensity      as double) as i,    -- A
            try_cast(Sub_metering_1        as double) as s1,   -- Wh in the minute
            try_cast(Sub_metering_2        as double) as s2,
            try_cast(Sub_metering_3        as double) as s3
        from raw
        """
    )
    return con


def one(db, sql):
    return db.execute(sql).fetchone()


def test_header_is_the_nine_uci_columns(db):
    cols = [c[0] for c in db.execute("describe raw").fetchall()]
    assert cols == UCI_COLUMNS


def test_row_count_matches_uci(db):
    assert one(db, "select count(*) from raw")[0] == UCI_ROWS


def test_every_minute_between_the_endpoints_is_present_exactly_once(db):
    # UCI: "All calendar timestamps are present in the dataset"
    n, distinct, first, last = one(db, "select count(*), count(distinct ts), min(ts), max(ts) from r")
    minutes_in_span = int((last - first).total_seconds() // 60) + 1
    assert n == minutes_in_span
    assert distinct == n
    # UCI: "between December 2006 and November 2010 (47 months)"
    assert (first.year, first.month) == (2006, 12)
    assert (last.year, last.month) == (2010, 11)


def test_missing_readings_are_all_or_nothing(db):
    assert one(db, "select count(*) from r where p is null")[0] == MISSING_READINGS
    assert abs(MISSING_READINGS / UCI_ROWS - 0.0125) < 0.0002          # UCI: "nearly 1,25%"
    # a missing reading has no measurement at all, and a complete one has all seven
    assert one(db, """select count(*) from r where p is null
                      and (q is not null or v is not null or i is not null
                           or s1 is not null or s2 is not null or s3 is not null)""")[0] == 0
    assert one(db, """select count(*) from r where p is not null
                      and (q is null or v is null or i is null
                           or s1 is null or s2 is null or s3 is null)""")[0] == 0
    assert one(db, "select count(*) from r where p is not null")[0] == COMPLETE_READINGS


def test_missing_marker_is_question_mark_except_empty_sub_metering_3(db):
    # The reason the loader lands every column as STRING with no null_marker.
    forms = db.execute(
        """select Global_active_power, Voltage, Sub_metering_3, count(*)
           from raw where try_cast(Global_active_power as double) is null group by all"""
    ).fetchall()
    assert forms == [("?", "?", None, MISSING_READINGS)]


def test_meter_quantization(db):
    # These facts justify the tolerances in the two physics tests below.
    assert one(db, "select count(*) from r where abs(i*5 - round(i*5)) > 1e-9")[0] == 0        # 0.2 A steps
    assert one(db, "select count(*) from r where abs(p*1000 - round(p*1000)) > 1e-6")[0] == 0  # 1 W steps
    assert one(db, "select count(*) from r where s1 <> floor(s1) or s2 <> floor(s2) or s3 <> floor(s3)")[0] == 0


def test_energy_balance(db):
    # UCI: global_active_power*1000/60 - sub_metering_1 - sub_metering_2 - sub_metering_3
    # "represents the active energy consumed every minute (in watt hour) ... by electrical
    # equipment not measured in sub-meterings 1, 2 and 3", so it cannot be negative.
    # Each sub-meter counts whole-Wh pulses, so one minute can carry at most one pulse
    # that belongs to its neighbour: tolerate 1 Wh per meter at minute grain, none at hour grain.
    rem = "p*1000/60 - s1 - s2 - s3"
    assert one(db, f"select count(*) from r where p is not null and {rem} < -{3 * PULSE_WH}")[0] == 0
    assert one(db, f"""select count(*) from (
                          select sum({rem}) as hour_rem from r where p is not null
                          group by date_trunc('hour', ts)) where hour_rem < 0""")[0] == 0
    assert one(db, f"select sum({rem}) from r where p is not null")[0] > 0


def test_active_power_never_exceeds_apparent_power(db):
    # P = V * I * cos(phi) <= V * I. Intensity is reported in 0.2 A steps, so allow one step.
    assert one(db, f"""select count(*) from r where p is not null
                       and p*1000/v - i > {INTENSITY_QUANTUM_A}""")[0] == 0


def test_measures_are_non_negative_and_mains_is_live(db):
    assert one(db, """select count(*) from r where p is not null
                      and (p <= 0 or q < 0 or v <= 0 or i <= 0 or s1 < 0 or s2 < 0 or s3 < 0)""")[0] == 0


def test_golden_answers_recomputed_from_the_raw_file(db):
    # The three README claims, recomputed here. tests/test_golden_answers.py checks that
    # the warehouse, via the assistant's query path, gives the same answers.
    assert one(db, "select round(sum(s1)), round(sum(s2)), round(sum(s3)) from r") == (
        2_299_135.0, 2_661_031.0, 13_235_167.0)                       # Wh; zone 3 dominates
    assert one(db, "select hour(ts) from r group by 1 order by avg(p) desc limit 1")[0] == 20
    assert one(db, "select dayname(ts) from r group by 1 order by avg(p) desc limit 1")[0] == "Saturday"
