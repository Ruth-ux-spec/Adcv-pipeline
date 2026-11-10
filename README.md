# Module 1: Profiling

Part of the Automated Data Cleaning & Validation System.
Reads a raw CSV and produces profiling_report.json plus three charts.

## Files
- profiling/metadata.py : load_raw, infer_column_type, detect_semantic_type
- profiling/engine.py   : missing_report, cardinality_report, numeric_summary, rule_flags, profile_dataset
- profiling/viz.py      : missing_heatmap, correlation_heatmap, outlier_plot
- data/spotify_raw.csv  : sample raw dataset
- outputs/              : profiling_report.json and the three .png charts

## How to run
    import profiling.metadata as m
    import profiling.engine as e
    df = m.load_raw("data/spotify_raw.csv")
    report = e.profile_dataset(df, "outputs/profiling_report.json")

## Report structure
- rows, columns_count
- columns: for each column, type (inferred_type, numeric_share, mixed_type, semantic_type),
  missing (count, pct), cardinality (unique counts, top values) and flags
- numeric: statistics and correlation for the numeric columns

## Rule flags
- mixed_type_values : some values are numbers, some are text
- inconsistent_case_or_format : the same value is written in different cases
- high_missing_rate : 15 percent or more of the values are missing
- potential_pii : the column looks like an email or phone number

## Design decisions
- Every column is read as text first, so no mess is hidden before profiling.
- Placeholders such as NA, null and ? count as missing.
- A comma with a dot is a thousands separator; a lone comma is a decimal point.

## Result on the sample data
- 121 rows, 10 columns.
- Stream columns have 16, 24 and 24 missing values.
- 6 text columns are flagged for inconsistent case, and debut_year for mixed types.
- Total streams and lead streams are strongly correlated (0.895).
