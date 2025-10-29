#!/usr/bin/env python3
"""Clean and pivot WSOC CMJ peak power metrics."""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "raw_data" / "MASTER_all_CMJmetrics.csv"
OUTPUT_PATH = PROJECT_ROOT / "script" / "outputs" / "cmj_wsoc_peakpowerbm_wide.csv"

START_DATE = pd.Timestamp("2024-06-03")
METRIC_NAME = "Peak Power / BM"
ATHLETE_COL_CANDIDATES: List[str] = ["athlete_name", "name", "athlete"]
DATE_COL_CANDIDATES: List[str] = [
    "date",
    "recordedUTC",
    "recordedUtc",
    "recorded_at",
    "recordedAt",
]
VALUE_COL_CANDIDATES: List[str] = [
    "value",
    "metric_value",
    "meanVal",
    "mean_value",
]


def pick_athlete_column(df: pd.DataFrame) -> pd.DataFrame:
    for col in ATHLETE_COL_CANDIDATES:
        if col in df.columns:
            df = df.rename(columns={col: "athlete_name"})
            break
    else:
        raise KeyError(
            "None of the expected athlete name columns found; checked "
            f"{ATHLETE_COL_CANDIDATES}."
        )
    df["athlete_name"] = df["athlete_name"].astype(str).str.strip()
    return df


def ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
    for candidate in DATE_COL_CANDIDATES:
        if candidate in df.columns:
            parsed = pd.to_datetime(df[candidate], errors="coerce")
            if parsed.notna().any():
                try:
                    parsed = parsed.dt.tz_convert(None)
                except AttributeError:
                    try:
                        parsed = parsed.dt.tz_localize(None)
                    except (AttributeError, TypeError):
                        pass
                df = df.assign(date=parsed)
                print(f"Using '{candidate}' as source for date column.")
                return df
    raise KeyError(
        "None of the candidate date columns were found or parseable; checked "
        f"{DATE_COL_CANDIDATES}."
    )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input CMJ metrics file not found at {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH)
    print(f"Input rows: {len(df)}")

    df = ensure_date_column(df)
    df = df[df["date"].notna()].copy()
    print(f"Rows after valid date parsing: {len(df)}")

    df = df[df["date"] >= START_DATE].copy()
    print(f"Rows on/after {START_DATE.date()}: {len(df)}")

    if "typeName" not in df.columns:
        raise KeyError("Expected 'typeName' column for sport filtering.")

    wsoc_mask = df["typeName"].astype(str).str.strip().str.casefold() == "women's soccer"
    df = df[wsoc_mask].copy()
    print(f"Rows after Women's Soccer filter: {len(df)}")

    df = pick_athlete_column(df)

    if "definition.name" not in df.columns:
        raise KeyError("Expected 'definition.name' to identify metrics.")

    metric_mask = df["definition.name"].astype(str).str.strip() == METRIC_NAME
    df = df[metric_mask].copy()
    print(f"Rows matching metric '{METRIC_NAME}': {len(df)}")

    value_col = None
    for candidate in VALUE_COL_CANDIDATES:
        if candidate in df.columns:
            value_col = candidate
            break
    if value_col is None:
        raise KeyError(
            "None of the candidate value columns were found; checked "
            f"{VALUE_COL_CANDIDATES}."
        )
    print(f"Using '{value_col}' as metric value column.")

    df[METRIC_NAME] = pd.to_numeric(df[value_col], errors="coerce")
    df = df[df[METRIC_NAME].notna()].copy()
    print(f"Rows with numeric metric values: {len(df)}")

    context_columns = [col for col in ["team", "team_name"] if col in df.columns]
    id_columns = ["date", "athlete_name"] + context_columns

    grouped = df.groupby(id_columns, dropna=False)[METRIC_NAME].mean().reset_index()
    excluded_names = {
        "kenna",
        "mia",
        "isabelle",
        "betty",
        "claire",
        "jess",
        "jordyn",
        "allison zipoli",
    }
    before_filter = len(grouped)
    grouped = grouped[
        ~grouped["athlete_name"].astype(str).str.strip().str.lower().isin(excluded_names)
    ]
    removed_count = before_filter - len(grouped)

    grouped.sort_values(by=["date", "athlete_name"], inplace=True)
    grouped.reset_index(drop=True, inplace=True)

    grouped["grid_week"] = ((grouped["date"] - START_DATE).dt.days // 7) + 1

    unique_athletes = grouped["athlete_name"].nunique()
    date_min = grouped["date"].min()
    date_max = grouped["date"].max()

    grouped["date"] = grouped["date"].dt.strftime("%m/%d/%Y")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    grouped.to_csv(OUTPUT_PATH, index=False)

    grid_week_min = grouped["grid_week"].min()
    grid_week_max = grouped["grid_week"].max()

    print(f"Unique WSOC athletes: {unique_athletes}")
    print(f"Output date range: {date_min} → {date_max}")
    print(f"Grid week range: {grid_week_min} → {grid_week_max}")
    if removed_count:
        print(f"Rows removed for excluded athletes: {removed_count}")
    print("Preview:")
    print(grouped.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
