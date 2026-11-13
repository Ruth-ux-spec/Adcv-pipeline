
import argparse
import logging
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from profiling.metadata import load_raw
from profiling.engine import profile_dataset
from profiling.viz import correlation_heatmap, missing_heatmap, outlier_plot
from cleaning.cleaner import clean_dataset
from validation.validator import validate_dataset

log = logging.getLogger("adcv")


def setup_logging(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    log_path = os.path.join(output_dir, "pipeline.log")
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(log_path, mode="w", encoding="utf-8"),
    ]
    for handler in handlers:
        handler.setFormatter(fmt)
        log.addHandler(handler)


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(path):
    if os.path.isabs(path):
        return path
    return os.path.join(ROOT, path)


def run_pipeline(config_path):
    cfg = load_config(config_path)
    input_file = resolve(cfg["input_file"])
    output_dir = resolve(cfg["output_dir"])
    columns = cfg["numeric_columns"]
    setup_logging(output_dir)
    started = time.time()
    log.info("Pipeline started")
    log.info("Input file: %s", input_file)

    log.info("Step 1 of 3: profiling")
    raw = load_raw(input_file)
    log.info("Loaded %d rows and %d columns", raw.shape[0], raw.shape[1])
    profile_dataset(raw, os.path.join(output_dir, "profiling_report.json"))
    missing_heatmap(raw, os.path.join(output_dir, "missing_heatmap.png"))
    correlation_heatmap(raw, columns, os.path.join(output_dir, "correlation_heatmap.png"))
    outlier_plot(raw, columns, os.path.join(output_dir, "outlier_plot.png"))
    log.info("Profiling report and 3 charts saved")

    log.info("Step 2 of 3: cleaning")
    cleaned, cleaning = clean_dataset(raw, columns, output_dir)
    log.info("Rows %d -> %d", cleaning["rows_before"], cleaning["rows_after"])
    log.info(
        "Quality score %s -> %s",
        cleaning["quality_before"]["overall"],
        cleaning["quality_after"]["overall"],
    )

    log.info("Step 3 of 3: validation")
    csv_path = os.path.join(output_dir, "cleaned_data.csv")
    validation = validate_dataset(csv_path, output_dir)
    log.info("Validation status: %s", validation["status"])
    log.info("Health score: %s", validation["health_score"])

    log.info("Pipeline finished in %.1f seconds", time.time() - started)
    return validation["status"]


def main():
    parser = argparse.ArgumentParser(
        description="Automated Data Cleaning and Validation System"
    )
    parser.add_argument(
        "--config",
        default=os.path.join(ROOT, "config.yaml"),
        help="path to the YAML settings file",
    )
    args = parser.parse_args()
    try:
        status = run_pipeline(args.config)
    except Exception:
        log.exception("Pipeline failed")
        return 1
    if status == "PASS":
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
