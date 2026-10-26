"""The loader stamps every raw row with the time it was loaded, so dbt source freshness
has something to measure."""
from ingestion.load_to_bigquery import stamp_loaded_at


def test_stamp_appends_loaded_at_to_the_header_and_every_row(tmp_path):
    src = tmp_path / "raw.txt"
    src.write_text(
        "Date;Time;Global_active_power\n"
        "16/12/2006;17:24:00;4.216\n"
        "16/12/2006;17:25:00;?\n"
    )
    dst = tmp_path / "stamped.txt"

    rows = stamp_loaded_at(src, dst, "2026-10-26T02:00:00Z")

    assert rows == 2
    assert dst.read_text().splitlines() == [
        "Date;Time;Global_active_power;_loaded_at",
        "16/12/2006;17:24:00;4.216;2026-10-26T02:00:00Z",
        "16/12/2006;17:25:00;?;2026-10-26T02:00:00Z",
    ]
