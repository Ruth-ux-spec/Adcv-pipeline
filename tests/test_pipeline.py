
import os
import sys

import yaml

import pipeline


def test_load_config_reads_settings(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump({"input_file": "a.csv", "output_dir": "out"}))
    cfg = pipeline.load_config(str(path))
    assert cfg["input_file"] == "a.csv"


def test_resolve_keeps_absolute_and_joins_relative():
    absolute = os.path.abspath("somewhere")
    assert pipeline.resolve(absolute) == absolute
    assert pipeline.resolve("data/x.csv") == os.path.join(pipeline.ROOT, "data/x.csv")


def test_full_pipeline_run_passes_and_writes_outputs(tmp_path):
    cfg = {
        "input_file": os.path.join(pipeline.ROOT, "data", "spotify_raw.csv"),
        "output_dir": str(tmp_path / "out"),
        "name_column": "artist_name",
        "numeric_columns": ["total_streams_m", "lead_streams_m", "feature_streams_m"],
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    status = pipeline.run_pipeline(str(cfg_path))
    assert status == "PASS"
    for name in ["cleaned_data.csv", "cleaning_log.json", "validation_report.json", "pipeline.log"]:
        assert (tmp_path / "out" / name).exists()


def test_missing_config_gives_error_exit_code(tmp_path, monkeypatch):
    bad = str(tmp_path / "nope.yaml")
    monkeypatch.setattr(sys, "argv", ["pipeline.py", "--config", bad])
    assert pipeline.main() == 1
