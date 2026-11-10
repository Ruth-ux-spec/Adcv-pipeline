import pandas as pd
from profiling.metadata import is_missing


def missing_report(df):
    """Count missing values per column, including placeholders like NA and ?."""
    report = {}
    for col in df.columns:
        count = int(sum(is_missing(v) for v in df[col]))
        report[col] = {
            "missing_count": count,
            "missing_pct": round(100 * count / len(df), 1),
        }
    return report


def cardinality_report(df):
    """Count distinct values per column, and again ignoring upper/lower case."""
    report = {}
    for col in df.columns:
        values = [str(v).strip() for v in df[col] if not is_missing(v)]
        top = pd.Series(values).value_counts().head(3).to_dict() if values else {}
        report[col] = {
            "unique_count": len(set(values)),
            "unique_case_insensitive": len(set(v.lower() for v in values)),
            "top_values": top,
        }
    return report


def to_number(value):
    """Turn messy numeric text such as 28797,6 or 25,574.20 into a float."""
    s = str(value).strip()
    if is_missing(s):
        return float("nan")
    if "," in s and "." in s:
        s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def numeric_summary(df, columns):
    """Basic statistics and a correlation matrix for the numeric columns."""
    nums = pd.DataFrame({c: df[c].map(to_number) for c in columns})
    stats = nums.describe().round(2).to_dict()
    corr = nums.corr().round(3).to_dict()
    return {"statistics": stats, "correlation": corr}


import json
from profiling.metadata import infer_column_type, detect_semantic_type


def rule_flags(column, meta, miss, card):
    flags = []
    if meta["mixed_type"]:
        flags.append("mixed_type_values")
    if card["unique_count"] > card["unique_case_insensitive"]:
        flags.append("inconsistent_case_or_format")
    if miss["missing_pct"] >= 15:
        flags.append("high_missing_rate")
    if meta["semantic_type"] in ("email", "phone"):
        flags.append("potential_pii")
    return flags


def profile_dataset(df, output_path=None):
    miss = missing_report(df)
    card = cardinality_report(df)
    columns = {}
    numeric_cols = []
    for col in df.columns:
        meta = infer_column_type(df[col])
        meta["semantic_type"] = detect_semantic_type(df[col], col)
        if meta["inferred_type"] == "numeric" and meta["semantic_type"] != "year":
            numeric_cols.append(col)
        columns[col] = {
            "type": meta,
            "missing": miss[col],
            "cardinality": card[col],
            "flags": rule_flags(col, meta, miss[col], card[col]),
        }
    report = {
        "rows": len(df),
        "columns_count": len(df.columns),
        "columns": columns,
        "numeric": numeric_summary(df, numeric_cols) if numeric_cols else {},
    }
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
    return report
