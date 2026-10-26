"""Golden answers: the warehouse, reached through the assistant's own query path, must give
the same answers as the raw file. tests/test_raw_profile.py recomputes every literal below
with DuckDB, an engine that never touches BigQuery.

Layer 1 runs hand-written reference SQL through run_sql(): no model involved, one small
BigQuery query each, works on the sandbox.
Layer 2 asks Gemini for the SQL (to_sql) and runs it. That is a paid Vertex AI call, so it
only runs when POWERWATCH_VERTEX_EVAL=1 is set.
"""
import os

import pytest

pytestmark = pytest.mark.bigquery

try:
    from ai_assistant.nl_to_sql import run_sql, to_sql
except SystemExit as e:  # GCP_PROJECT_ID unset: nothing to query
    pytest.skip(str(e), allow_module_level=True)

DS = os.environ.get("BQ_DATASET", "powerwatch")

# From the raw file (DuckDB, 2026-10-26): Wh per zone, complete readings, peak hour, busiest day.
ZONE_TOTALS_WH = {1: 2_299_135, 2: 2_661_031, 3: 13_235_167}
COMPLETE_READINGS = 2_049_280

GOLDEN = [
    (
        "Which zone used the most energy overall?",
        f"""SELECT z.zone_name FROM `{DS}.fct_zone_energy` f JOIN `{DS}.dim_zone` z USING (zone_key)
            GROUP BY 1 ORDER BY SUM(f.energy_wh) DESC LIMIT 1""",
        "Water Heater & AC",
    ),
    (
        "Which hour of the day has the highest average active power?",
        f"""SELECT t.hour FROM `{DS}.fct_household_load` f JOIN `{DS}.dim_time` t USING (time_key)
            GROUP BY 1 ORDER BY AVG(f.active_power) DESC LIMIT 1""",
        20,
    ),
    (
        "Which day of the week has the highest average household load?",
        f"""SELECT d.day_of_week FROM `{DS}.fct_household_load` f JOIN `{DS}.dim_date` d USING (date_key)
            GROUP BY 1 ORDER BY AVG(f.active_power) DESC LIMIT 1""",
        "Saturday",
    ),
]


def first_value(rows):
    return next(iter(rows[0].values()))


@pytest.mark.parametrize("question, reference_sql, expected", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_warehouse_gives_the_raw_files_answer(question, reference_sql, expected):
    assert first_value(run_sql(reference_sql)) == expected


def test_fact_row_counts_match_the_raw_file():
    assert first_value(run_sql(f"SELECT COUNT(*) FROM `{DS}.fct_household_load`")) == COMPLETE_READINGS
    assert first_value(run_sql(f"SELECT COUNT(*) FROM `{DS}.fct_zone_energy`")) == 3 * COMPLETE_READINGS


def test_zone_totals_match_the_raw_file_exactly():
    rows = run_sql(f"SELECT zone_key, ROUND(SUM(energy_wh)) AS wh FROM `{DS}.fct_zone_energy` GROUP BY 1")
    assert {r["zone_key"]: int(r["wh"]) for r in rows} == ZONE_TOTALS_WH


@pytest.mark.vertex
@pytest.mark.skipif(not os.environ.get("POWERWATCH_VERTEX_EVAL"), reason="paid Vertex AI call; set POWERWATCH_VERTEX_EVAL=1")
@pytest.mark.parametrize("question, reference_sql, expected", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_assistant_answers_the_golden_question(question, reference_sql, expected):
    rows = run_sql(to_sql(question))
    assert expected in rows[0].values(), rows[0]
