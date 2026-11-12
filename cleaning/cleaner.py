import re
import pandas as pd
from profiling.metadata import is_missing
from profiling.engine import to_number

PLAIN_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
PLAIN_YEAR = re.compile(r"^(19|20)\d{2}$")


def add_log(log, column, action, count):
    log.append({"column": column, "action": action, "values_changed": int(count)})


def count_not_matching(series, pattern):
    return sum(1 for v in series if not pattern.match(str(v).strip()))


def clean_numeric_columns(df, columns, log):
    """Convert messy numeric text to floats and record what changed."""
    out = df.copy()
    for col in columns:
        changed = count_not_matching(out[col], PLAIN_NUMBER)
        out[col] = out[col].map(to_number)
        add_log(log, col, "converted text to float", changed)
    return out


def to_year(value):
    s = str(value).strip().replace("'", "")
    if is_missing(s):
        return float("nan")
    try:
        y = int(float(s))
    except ValueError:
        return float("nan")
    if y < 100:
        y += 2000 if y <= 26 else 1900
    return float(y) if 1900 <= y <= 2026 else float("nan")


def clean_year_column(df, column, log):
    """Turn two-digit and messy years into four-digit years."""
    out = df.copy()
    changed = count_not_matching(out[column], PLAIN_YEAR)
    out[column] = out[column].map(to_year)
    add_log(log, column, "standardised years to four digits", changed)
    return out


SEX_MAP = {"f": "Female", "female": "Female", "m": "Male", "male": "Male", "mixed": "Mixed"}
COUNTRY_MAP = {
    "us": "United States", "usa": "United States", "u.s.a": "United States",
    "united states": "United States", "uk": "United Kingdom",
    "u.k.": "United Kingdom", "united kingdom": "United Kingdom",
    "scotland": "United Kingdom", "korea, south": "South Korea",
    "south korea": "South Korea",
}


def fix_sex(value):
    return SEX_MAP.get(str(value).strip().lower(), float("nan"))


def fix_country(value):
    s = str(value).strip().lower()
    if s == "":
        return float("nan")
    return COUNTRY_MAP.get(s, s.title().replace(" And ", " and "))


def fix_title(value):
    s = str(value).strip().title()
    if s == "":
        return float("nan")
    return "EDM" if s == "Edm" else s


def standardise(df, column, func, log, action):
    """Apply one fixing function to a column and record how many values changed."""
    out = df.copy()
    before = out[column].copy()
    out[column] = out[column].map(func)
    changed = sum(1 for b, a in zip(before, out[column]) if str(b) != str(a))
    add_log(log, column, action, changed)
    return out


def clean_text_columns(df, log):
    out = standardise(df, "sex", fix_sex, log, "standardised to Male, Female or Mixed")
    out = standardise(out, "country_of_origin", fix_country, log, "unified country names")
    out = standardise(out, "primary_language", fix_title, log, "standardised casing")
    out = standardise(out, "primary_genre", fix_title, log, "standardised casing")
    out = standardise(out, "artist_type", fix_title, log, "standardised casing")
    return out


import difflib


def drop_junk_rows(df, name_column, log):
    """Remove rows where everything except the name is empty."""
    others = [c for c in df.columns if c != name_column]
    mask = df[others].apply(lambda col: col.map(is_missing)).all(axis=1)
    add_log(log, name_column, "removed empty or unknown rows", mask.sum())
    return df[~mask].reset_index(drop=True)


def name_key(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def find_duplicate_groups(df, name_column, threshold=0.88):
    """Group row positions whose artist names match or nearly match."""
    keys = [name_key(n) for n in df[name_column]]
    groups = []
    for i, k in enumerate(keys):
        if k == "":
            continue
        placed = False
        for g in groups:
            ref = keys[g[0]]
            if k == ref or difflib.SequenceMatcher(None, k, ref).ratio() >= threshold:
                g.append(i)
                placed = True
                break
        if not placed:
            groups.append([i])
    return [g for g in groups if len(g) > 1]


def remove_duplicates(df, name_column, log):
    """Keep one row per artist and log every conflict for human review."""
    out = df.reset_index(drop=True)
    drop = []
    for g in find_duplicate_groups(out, name_column):
        rows = out.loc[g]
        totals = rows["total_streams_m"].dropna()
        if len(totals) > 1 and totals.max() > 1.1 * totals.min():
            keeper = totals.idxmax()
            log.append({
                "column": name_column,
                "action": "conflicting totals, kept the larger",
                "values_changed": 0,
                "detail": str(list(rows[name_column])) + " totals " + str(list(totals)),
            })
        else:
            keeper = rows.notna().sum(axis=1).idxmax()
        drop.extend(i for i in g if i != keeper)
    add_log(log, name_column, "removed duplicate artist rows", len(drop))
    return out.drop(index=drop).reset_index(drop=True)


def impute_total_streams(df, log):
    """Fill missing totals: lead + feature first, then the genre median."""
    out = df.copy()
    both = (out["total_streams_m"].isna() & out["lead_streams_m"].notna()
            & out["feature_streams_m"].notna())
    out.loc[both, "total_streams_m"] = out["lead_streams_m"] + out["feature_streams_m"]
    add_log(log, "total_streams_m", "filled with lead + feature streams", both.sum())

    medians = out.groupby("primary_genre")["total_streams_m"].transform("median")
    need = out["total_streams_m"].isna() & medians.notna()
    out.loc[need, "total_streams_m"] = medians[need]
    add_log(log, "total_streams_m", "filled with genre median", need.sum())

    rest = out["total_streams_m"].isna()
    out.loc[rest, "total_streams_m"] = out["total_streams_m"].median()
    add_log(log, "total_streams_m", "filled with overall median", rest.sum())
    return out


KEEP_UPPER = {"BTS", "NF", "SZA", "TWICE", "XXXTENTACION"}


def fix_name(value):
    s = re.sub(r"\s+", " ", str(value)).strip()
    if s.upper() in KEEP_UPPER:
        return s.upper()
    if s.islower() or (s.isupper() and len(s) > 3):
        return s.title()
    return s


def clean_names(df, name_column, log):
    """Strip stray spaces and fix all-lower or all-upper artist names."""
    out = df.copy()
    before = out[name_column].copy()
    out[name_column] = out[name_column].map(fix_name)
    changed = sum(1 for b, a in zip(before, out[name_column]) if str(b) != str(a))
    add_log(log, name_column, "trimmed spaces and fixed casing", changed)
    return out


def cell_missing(v):
    if pd.isna(v):
        return True
    return is_missing(str(v))


def quality_score(df, name_column, numeric_columns):
    """Score a dataset out of 100 using completeness, uniqueness, validity."""
    total_cells = df.shape[0] * df.shape[1]
    missing = sum(cell_missing(v) for col in df.columns for v in df[col])
    completeness = 100 - missing / total_cells * 100

    keys = [name_key(n) for n in df[name_column]]
    keys = [k for k in keys if k != ""]
    repeats = len(keys) - len(set(keys))
    uniqueness = 100 - repeats / max(len(keys), 1) * 100

    checked = 0
    bad = 0
    for col in numeric_columns:
        for v in df[col]:
            if cell_missing(v):
                continue
            checked += 1
            if not PLAIN_NUMBER.match(str(v).strip()):
                bad += 1
    validity = 100 - bad / max(checked, 1) * 100

    score = (completeness + uniqueness + validity) / 3
    return {
        "completeness": round(completeness, 2),
        "uniqueness": round(uniqueness, 2),
        "validity": round(validity, 2),
        "overall": round(score, 2),
    }


import json
import os


def clean_dataset(raw, numeric_columns, output_dir):
    """Run every cleaning step in order and save the two output files."""
    log = []
    df = clean_numeric_columns(raw, numeric_columns, log)
    df = clean_year_column(df, "debut_year", log)
    df = clean_text_columns(df, log)
    df = drop_junk_rows(df, "artist_name", log)
    df = remove_duplicates(df, "artist_name", log)
    df = impute_total_streams(df, log)
    df = clean_names(df, "artist_name", log)

    before = quality_score(raw, "artist_name", numeric_columns)
    after = quality_score(df, "artist_name", numeric_columns)
    report = {
        "rows_before": int(len(raw)),
        "rows_after": int(len(df)),
        "quality_before": before,
        "quality_after": after,
        "quality_change": round(after["overall"] - before["overall"], 2),
        "steps": log,
    }

    os.makedirs(output_dir, exist_ok=True)
    df.to_csv(os.path.join(output_dir, "cleaned_data.csv"), index=False)
    with open(os.path.join(output_dir, "cleaning_log.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    return df, report
