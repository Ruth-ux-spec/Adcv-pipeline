import re
import pandas as pd

MISSING_TOKENS = {"", "na", "n/a", "null", "?", "nan", "none"}
NUMERIC_PATTERN = re.compile(
    r"^-?\d+([.,]\d+)?$|^-?\d{1,3}(,\d{3})+(\.\d+)?$"
)


def load_raw(path):
    """Read every column as text so no information is lost before profiling."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = (df.columns.str.strip().str.lower()
                  .str.replace(r"[^\w]+", "_", regex=True).str.strip("_"))
    return df


def is_missing(value):
    return str(value).strip().lower() in MISSING_TOKENS


def infer_column_type(series):
    """Return the inferred type and whether the column mixes numbers and text."""
    values = [str(v).strip() for v in series if not is_missing(v)]
    if not values:
        return {"inferred_type": "empty", "numeric_share": 0.0, "mixed_type": False}
    share = sum(bool(NUMERIC_PATTERN.match(v)) for v in values) / len(values)
    return {
        "inferred_type": "numeric" if share >= 0.5 else "text",
        "numeric_share": round(share, 3),
        "mixed_type": 0 < share < 1,
    }


EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,15}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{1,2}/\d{1,2}/\d{2,4}$")
YEAR_RE = re.compile(r"^'?\d{2}$|^(19|20)\d{2}$")


def _share(values, pattern):
    return sum(bool(pattern.match(v)) for v in values) / len(values)


def detect_semantic_type(series, column_name=""):
    """Guess the meaning of a column from its values and its name."""
    values = [str(v).strip() for v in series if not is_missing(v)]
    if not values:
        return "empty"
    name = column_name.lower()
    if _share(values, EMAIL_RE) >= 0.8:
        return "email"
    if _share(values, DATE_RE) >= 0.8:
        return "date"
    if "year" in name or _share(values, YEAR_RE) >= 0.8:
        return "year"
    if _share(values, PHONE_RE) >= 0.8:
        return "phone"
    if name.endswith("id") or "_id" in name:
        return "id"
    if "name" in name:
        return "name"
    if infer_column_type(series)["inferred_type"] == "numeric":
        return "numeric_measure"
    if len(set(values)) / len(values) < 0.4:
        return "categorical"
    return "free_text"
