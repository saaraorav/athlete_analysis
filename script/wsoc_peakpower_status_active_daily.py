#!/usr/bin/env python3
"""Aggregate CMJ Peak Power for dates where athletes meet weekly load thresholds."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PEAK_PATH = PROJECT_ROOT / "script" / "outputs" / "cmj_wsoc_peakpowerbm_wide.csv"
STATUS_SOURCES = [
    PROJECT_ROOT / "script" / "outputs" / "wsoc_aligned_gamedays.csv",
    PROJECT_ROOT / "script" / "outputs" / "wsoc_playertek_practice_only_with_status.csv",
]
OUTPUT_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_peakpower_status_active_daily.csv"
METRIC_COL = "Peak Power / BM"
START_WEEK = pd.Timestamp("2024-06-03")
MIN_ACTIVE = 7


def week_month_label(grid_week: int) -> str:
    monday = START_WEEK + pd.Timedelta(weeks=grid_week - 1)
    week_days = pd.date_range(monday, periods=7, freq="D")
    counts = week_days.to_period("M").value_counts()
    max_count = counts.max()
    candidate_periods = counts[counts == max_count].index.tolist()
    monday_period = monday.to_period("M")
    if monday_period in candidate_periods:
        chosen_period = monday_period
    else:
        chosen_period = sorted(candidate_periods)[0]
    return chosen_period.to_timestamp().strftime("%b %Y")


def load_status() -> pd.DataFrame:
    frames = []
    for path in STATUS_SOURCES:
        if not path.exists():
            print(f"Warning: status source missing ({path}); skipping.")
            continue
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
        df["grid_week"] = pd.to_numeric(df.get("grid_week"), errors="coerce").astype("Int64")
        df["athlete_key"] = df.get("athlete_name_full", "").astype(str).str.strip().str.lower()
        frames.append(df)

    if not frames:
        raise FileNotFoundError("No status sources found.")

    status = pd.concat(frames, ignore_index=True)
    status = status[status["date"].notna()].copy()
    status = status[status["status_weekly"].fillna(False)].copy()
    status = status.drop_duplicates(subset=["athlete_key", "grid_week"])
    return status[["athlete_key", "grid_week", "date"]]


def main() -> None:
    if not PEAK_PATH.exists():
        raise FileNotFoundError(f"Peak power file not found at {PEAK_PATH}")

    peak_df = pd.read_csv(PEAK_PATH)
    total_rows = len(peak_df)

    peak_df["date"] = pd.to_datetime(peak_df.get("date"), errors="coerce")
    peak_df["grid_week"] = pd.to_numeric(peak_df.get("grid_week"), errors="coerce").astype("Int64")
    peak_df["athlete_key"] = peak_df.get("athlete_name", "").astype(str).str.strip().str.lower()
    peak_df = peak_df[peak_df["date"].notna()].copy()

    status_df = load_status()

    merged = peak_df.merge(
        status_df,
        on=["athlete_key", "grid_week"],
        how="inner",
        suffixes=("", "_status"),
    )
    filtered_rows = len(merged)

    daily = (
        merged.groupby(merged["date"].dt.normalize())
        .agg(
            avg_peak_power=(METRIC_COL, "mean"),
            n_athletes=("athlete_key", "nunique"),
            grid_week=("grid_week", "first"),
        )
        .reset_index()
    )

    qualified = daily[daily["n_athletes"] >= MIN_ACTIVE].copy()
    qualified["month"] = qualified["grid_week"].astype(int).apply(week_month_label)
    qualified.sort_values("date", inplace=True)
    qualified["date"] = qualified["date"].dt.strftime("%m/%d/%Y")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    qualified.to_csv(OUTPUT_PATH, index=False)

    print(f"Peak power rows processed: {total_rows}")
    print(f"Rows after status join: {filtered_rows}")
    print(f"Daily records after >= {MIN_ACTIVE} athletes filter: {len(qualified)}")
    if not qualified.empty:
        print("First 5 rows:")
        print(qualified.head(5).to_string(index=False))
        print("Last 5 rows:")
        print(qualified.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
