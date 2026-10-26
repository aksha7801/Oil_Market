"""Pipeline for the oil_market dashboard.

Offline mode (default, used by the checker): rebuild the processed file from the
committed sample. No network, writes only the declared processed output.
Live mode: validate and merge new vintages that the analyst has transcribed
into data/raw/new_vintages.csv from the agencies' monthly reports.
"""
from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample" / "agency_forecasts.csv"
PROCESSED = ROOT / "data" / "processed" / "agency_forecasts.csv"
RAW_NEW = ROOT / "data" / "raw" / "new_vintages.csv"

COLUMNS = ["record_id", "agency", "report_month", "target_year",
           "demand_growth_mbd", "demand_level_mbd", "value_basis"]
AGENCIES = {"IEA", "OPEC", "EIA"}
BASIS = {"reported", "derived"}


def read_csv(path: Path) -> pd.DataFrame:
    """Read with explicit dtypes; only empty fields are missing."""
    df = pd.read_csv(
        path,
        dtype={"record_id": str, "agency": str, "report_month": str,
               "value_basis": str},
        keep_default_na=False,
        na_values=[""],
    )
    df["target_year"] = df["target_year"].astype("int64")
    df["demand_growth_mbd"] = pd.to_numeric(df["demand_growth_mbd"], errors="raise")
    df["demand_level_mbd"] = pd.to_numeric(df["demand_level_mbd"], errors="raise")
    return df[COLUMNS]


def validate(df: pd.DataFrame) -> pd.DataFrame:
    if list(df.columns) != COLUMNS:
        raise ValueError(f"unexpected columns: {list(df.columns)}")
    if not set(df["agency"]) <= AGENCIES:
        raise ValueError("unknown agency")
    if not set(df["value_basis"]) <= BASIS:
        raise ValueError("unknown value_basis")
    if df["record_id"].duplicated().any():
        raise ValueError("duplicate record_id")
    pd.to_datetime(df["report_month"], format="%Y-%m-%d", errors="raise")
    expected = (df["report_month"].str[:7] + "|" + df["agency"] + "|"
                + df["target_year"].astype(str))
    if (expected != df["record_id"]).any():
        raise ValueError("record_id must be '<YYYY-MM>|<agency>|<target_year>'")
    if df["demand_growth_mbd"].isna().any():
        raise ValueError("demand_growth_mbd is required")
    if not df["demand_growth_mbd"].between(-10, 10).all():
        raise ValueError("demand_growth_mbd outside -10..10 mb/d")
    lvl = df["demand_level_mbd"].dropna()
    if not lvl.between(90, 115).all():
        raise ValueError("demand_level_mbd outside 90..115 mb/d")
    return df.sort_values(["report_month", "target_year", "agency"]).reset_index(drop=True)


def _atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    os.close(fd)
    try:
        df.to_csv(tmp, index=False, na_rep="", lineterminator="\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def build_offline() -> pd.DataFrame:
    df = validate(read_csv(SAMPLE))
    _atomic_write(df, PROCESSED)
    return df


def build_live() -> pd.DataFrame:
    """Merge analyst-transcribed vintages (data/raw/new_vintages.csv) into the sample."""
    base = read_csv(SAMPLE)
    if RAW_NEW.exists():
        new = read_csv(RAW_NEW)
        base = pd.concat([base, new]).drop_duplicates("record_id", keep="last")
    df = validate(base)
    _atomic_write(df, SAMPLE)
    _atomic_write(df, PROCESSED)
    return df


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["offline", "live"], default="offline")
    a = p.parse_args()
    df = build_offline() if a.mode == "offline" else build_live()
    print(f"wrote {len(df)} rows to {PROCESSED}")


if __name__ == "__main__":
    main()
