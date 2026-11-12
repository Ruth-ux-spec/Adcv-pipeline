
import pandas as pd
from cleaning.cleaner import (
    fix_name, fix_sex, fix_country, to_year, name_key,
    drop_junk_rows, clean_names, quality_score,
)


def test_fix_name_trims_and_fixes_case():
    assert fix_name("  taylor   swift ") == "Taylor Swift"


def test_fix_name_keeps_known_capitals():
    assert fix_name("bts") == "BTS"


def test_fix_sex_standard_values():
    assert fix_sex("f") == "Female"
    assert fix_sex("m") == "Male"


def test_fix_country_standard_values():
    assert fix_country("usa") == "United States"
    assert fix_country("uk") == "United Kingdom"


def test_to_year_two_digit():
    assert to_year("'08") == 2008


def test_to_year_out_of_range_is_missing():
    assert pd.isna(to_year("1850"))


def test_name_key_ignores_case_and_symbols():
    assert name_key("Bad  Bunny!") == "badbunny"


def test_drop_junk_rows_removes_empty_rows():
    df = pd.DataFrame({"artist_name": ["A", "B"], "x": ["1", ""]})
    log = []
    out = drop_junk_rows(df, "artist_name", log)
    assert len(out) == 1


def test_clean_names_logs_changes():
    df = pd.DataFrame({"artist_name": ["  taylor swift", "Eminem"]})
    log = []
    out = clean_names(df, "artist_name", log)
    assert out["artist_name"][0] == "Taylor Swift"
    assert log[-1]["values_changed"] == 1


def test_quality_score_perfect_data():
    df = pd.DataFrame({"artist_name": ["A", "B"], "streams": ["1", "2"]})
    result = quality_score(df, "artist_name", ["streams"])
    assert result["overall"] == 100.0


def test_quality_score_drops_with_missing_values():
    df = pd.DataFrame({"artist_name": ["A", "B"], "streams": ["1", ""]})
    result = quality_score(df, "artist_name", ["streams"])
    assert result["completeness"] < 100
