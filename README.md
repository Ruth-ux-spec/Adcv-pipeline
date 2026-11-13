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


## Module 3: Validation

Checks the cleaned data and saves outputs/validation_report.json.

### Validation rules
Each rule counts how many rows fail it and lists up to 3 example artists.
1. Debut year is between 1900 and 2026.
2. Stream numbers (total, lead, feature) are not negative.
3. Sex is Male, Female or Mixed.
4. Artist name is not blank.
5. Each artist name appears only once.
6. Lead streams + feature streams do not exceed total streams.

### Anomaly detection
Uses the IQR rule: a value is flagged if it is more than 3 x IQR outside the middle 50% of the data. An anomaly is unusual, not necessarily wrong (for example, very big artists such as Drake, Taylor Swift and Bad Bunny). Known limitation: stream data is heavily skewed, so the lower limit is negative and very small values can never be flagged.

### Health score
Health score = 50% rules + 30% completeness + 20% anomalies, each out of 100. Status is PASS only if no rule fails. Anomalies count for less because they are warnings, not errors.

### Results on the cleaned data
| Part | Score |
|---|---|
| Rules | 100.0 |
| Completeness | 95.28 |
| Anomalies | 97.48 |
| Overall health | 98.08 (PASS) |

### Tests
Run python -m pytest tests -q. There are 19 tests in total (11 for cleaning, 8 for validation). The validation tests build small datasets with one deliberate problem each and check that it is caught.

### How to run

    from validation.validator import validate_dataset
    report = validate_dataset("outputs/cleaned_data.csv", "outputs")


## Module 4: Automation

One command runs the whole system: profiling, cleaning, then validation.

### Quick start

    pip install -r requirements.txt
    python pipeline.py

To use a different settings file:

    python pipeline.py --config my_config.yaml

### Settings (config.yaml)
| Setting | Meaning |
|---|---|
| input_file | raw CSV to process |
| output_dir | folder for all results |
| name_column | column holding artist names |
| numeric_columns | stream columns used for charts and checks |

### What the pipeline does
1. *Profiling:* loads the raw file, saves profiling_report.json and 3 charts.
2. *Cleaning:* saves cleaned_data.csv and cleaning_log.json.
3. *Validation:* checks the cleaned file and saves validation_report.json.

Every step is written to outputs/pipeline.log with a timestamp, so a failure shows which step stopped.

### Exit codes
| Code | Meaning |
|---|---|
| 0 | Pipeline finished and validation PASSED |
| 1 | The pipeline failed with an error (see the log) |
| 2 | The pipeline finished but validation FAILED |

### Docker
A Dockerfile is included.

    docker build -t adcv-pipeline .
    docker run --rm -v "$(pwd)/outputs:/app/outputs" adcv-pipeline

Note: the Dockerfile follows the standard pattern but was not built on the author's computer, because Docker was not installed there.

### Tests
Run python -m pytest tests -q. There are 23 tests: 11 for cleaning, 8 for validation and 4 for the pipeline (reading settings, path handling, a full run, and a clean error exit when the config file is missing).

### Result on the Spotify artist data
| Measure | Value |
|---|---|
| Rows | 121 cleaned to 106 |
| Quality score | 89.67 to 98.43 |
| Validation | PASS, health score 98.08 |
| Run time | about 1.3 seconds |

### Project layout
- profiling/ Module 1: profiling engine and charts
- cleaning/ Module 2: cleaning pipeline and quality score
- validation/ Module 3: rules, anomaly detection, health score
- pipeline.py Module 4: command-line entry point
- config.yaml, requirements.txt, Dockerfile
- tests/ all tests
- outputs/ all generated files
