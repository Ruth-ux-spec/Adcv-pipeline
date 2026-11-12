
import pandas as pd

VALID_SEX = {"Male", "Female", "Mixed"}


def make_result(df, rule, column, mask):
    """Count rows that break a rule and keep up to 3 example names."""
    failed = int(mask.sum())
    names = [str(n) for n in df.loc[mask, "artist_name"].head(3)]
    return {
        "rule": rule,
        "column": column,
        "failed": failed,
        "passed": int(len(df) - failed),
        "examples": names,
    }


def check_rules(df):
    """Run every validation rule and return a list of results."""
    results = []

    year = df["debut_year"]
    bad_year = year.notna() & ((year < 1900) | (year > 2026))
    results.append(make_result(df, "debut year between 1900 and 2026", "debut_year", bad_year))

    for col in ["total_streams_m", "lead_streams_m", "feature_streams_m"]:
        results.append(make_result(df, "streams not negative", col, df[col] < 0))

    bad_sex = df["sex"].notna() & ~df["sex"].isin(VALID_SEX)
    results.append(make_result(df, "sex is Male, Female or Mixed", "sex", bad_sex))

    no_name = df["artist_name"].isna() | (df["artist_name"].astype(str).str.strip() == "")
    results.append(make_result(df, "artist name not blank", "artist_name", no_name))

    repeated = df["artist_name"].duplicated(keep=False) & ~no_name
    results.append(make_result(df, "artist name appears once", "artist_name", repeated))

    too_big = (df["lead_streams_m"] + df["feature_streams_m"]) > df["total_streams_m"] * 1.001
    results.append(make_result(df, "lead + feature not above total", "total_streams_m", too_big))

    return results


def find_outliers(df, column, factor=3.0):
    """Flag values far outside the middle of the data (IQR rule)."""
    values = df[column].dropna()
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    spread = q3 - q1
    low = q1 - factor * spread
    high = q3 + factor * spread
    mask = df[column].notna() & ((df[column] < low) | (df[column] > high))
    top = df.loc[mask].sort_values(column, ascending=False).head(3)
    examples = [str(n) + " (" + str(x) + ")" for n, x in zip(top["artist_name"], top[column])]
    return {
        "column": column,
        "outliers": int(mask.sum()),
        "lower_limit": round(float(low), 2),
        "upper_limit": round(float(high), 2),
        "examples": examples,
    }


def find_all_outliers(df, columns):
    return [find_outliers(df, col) for col in columns]


import json
import os


def validate_dataset(csv_path, output_dir):
    """Run all checks on a cleaned file and save validation_report.json."""
    df = pd.read_csv(csv_path)
    stream_cols = ["total_streams_m", "lead_streams_m", "feature_streams_m"]

    rules = check_rules(df)
    anomalies = find_all_outliers(df, stream_cols)

    checked = sum(r["passed"] + r["failed"] for r in rules)
    failed = sum(r["failed"] for r in rules)
    rule_score = 100 - failed / checked * 100

    total_cells = df.shape[0] * df.shape[1]
    completeness = 100 - float(df.isna().sum().sum()) / total_cells * 100

    flagged = sum(a["outliers"] for a in anomalies)
    anomaly_score = 100 - flagged / (len(df) * len(stream_cols)) * 100

    health = 0.5 * rule_score + 0.3 * completeness + 0.2 * anomaly_score
    status = "PASS" if failed == 0 else "FAIL"

    report = {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "status": status,
        "health_score": round(health, 2),
        "score_parts": {
            "rules": round(rule_score, 2),
            "completeness": round(completeness, 2),
            "anomalies": round(anomaly_score, 2),
        },
        "rule_results": rules,
        "anomalies": anomalies,
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "validation_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    return report
