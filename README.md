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


## Module 2: Cleaning

Cleans the raw Spotify artist data and saves outputs/cleaned_data.csv and outputs/cleaning_log.json.

### What the cleaning does (in order)
1. *Numbers:* converts text numbers to real numbers. A comma with a dot means thousands (1,234.5); a lone comma is a decimal point.
2. *Debut year:* two-digit years such as '08 become 2008. Years outside 1900-2026 are set to missing.
3. *Text columns:* standardises sex, country, language, genre and artist type (e.g. USA/US become United States).
4. *Junk rows:* removes rows where every column except the name is empty.
5. *Duplicates:* finds the same artist spelled slightly differently (fuzzy match, similarity 0.88 or higher) and keeps one row. If the two total-streams values differ by more than 10%, the larger one is kept and both values are written to the log for a human to review.
6. *Missing total streams:* filled with lead + feature streams, else the genre median, else the overall median.
7. *Artist names:* trims stray spaces and fixes all-lower or all-upper casing (BTS, NF, SZA, TWICE and XXXTENTACION stay in capitals).

### Results
| Measure | Before | After |
|---|---|---|
| Rows | 121 | 106 |
| Quality score (out of 100) | 89.67 | 98.43 |

The quality score is the average of completeness, uniqueness and validity. Some blanks remain on purpose, because values such as a missing debut year are not invented.

### Judgment call
Choosing the larger total when duplicates disagree is an assumption, not a proven fact. That is why every such conflict is logged.

### Cleaning log
cleaning_log.json holds the before/after quality scores and one entry per step: column, action and number of values changed.

### Tests
Run python -m pytest tests -q from the project folder. There are 11 tests covering names, sex, country, years, junk rows, logging and the quality score.

### How to run

    from cleaning.cleaner import clean_dataset
    final_df, report = clean_dataset(raw, numeric_columns, "outputs")
