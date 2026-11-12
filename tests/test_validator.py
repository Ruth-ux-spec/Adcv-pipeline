
import pandas as pd
from validation.validator import check_rules, find_outliers, validate_dataset


def good_data():
    return pd.DataFrame({
        "artist_name": ["A", "B", "C", "D"],
        "sex": ["Male", "Female", "Mixed", "Male"],
        "debut_year": [2000.0, 2010.0, 1995.0, 2015.0],
        "total_streams_m": [100.0, 200.0, 150.0, 120.0],
        "lead_streams_m": [80.0, 150.0, 100.0, 90.0],
        "feature_streams_m": [20.0, 50.0, 50.0, 30.0],
    })


def failures(results, rule):
    return sum(r["failed"] for r in results if r["rule"] == rule)


def test_good_data_passes_every_rule():
    results = check_rules(good_data())
    assert sum(r["failed"] for r in results) == 0


def test_bad_debut_year_is_caught():
    df = good_data()
    df.loc[0, "debut_year"] = 1850.0
    assert failures(check_rules(df), "debut year between 1900 and 2026") == 1


def test_negative_streams_are_caught():
    df = good_data()
    df.loc[1, "total_streams_m"] = -5.0
    assert failures(check_rules(df), "streams not negative") == 1


def test_invalid_sex_is_caught():
    df = good_data()
    df.loc[2, "sex"] = "Robot"
    assert failures(check_rules(df), "sex is Male, Female or Mixed") == 1


def test_repeated_names_are_caught():
    df = good_data()
    df.loc[1, "artist_name"] = "A"
    assert failures(check_rules(df), "artist name appears once") == 2


def test_lead_plus_feature_above_total_is_caught():
    df = good_data()
    df.loc[0, "lead_streams_m"] = 500.0
    assert failures(check_rules(df), "lead + feature not above total") == 1


def test_outlier_is_flagged():
    df = pd.DataFrame({
        "artist_name": list("ABCDEFGH"),
        "x": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 1000.0],
    })
    result = find_outliers(df, "x")
    assert result["outliers"] == 1


def test_report_file_is_written(tmp_path):
    csv_path = tmp_path / "clean.csv"
    good_data().to_csv(csv_path, index=False)
    report = validate_dataset(str(csv_path), str(tmp_path))
    assert report["status"] == "PASS"
    assert (tmp_path / "validation_report.json").exists()
