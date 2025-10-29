#!/usr/bin/env python3
"""Compute WSOC active flags (per date and per week) based on field time."""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIMARY_INPUT = PROJECT_ROOT / "script" / "outputs" / "wsoc_playertek_combined_aligned.csv"
FALLBACK_INPUT = Path("/mnt/data/wsoc_playertek_combined_aligned.csv")
OUTPUT_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_weekly_with_status.csv"

START_WEEK = pd.Timestamp("2024-06-03", tz="UTC").tz_convert(None)
SECONDS_PER_MINUTE = 60
DAILY_ACTIVE_THRESHOLD = 45 * SECONDS_PER_MINUTE  # 2700 seconds

COLUMN_ORDER: List[str] = [
    "athlete_name_full",
    "catapult_athlete_id",
    "status",
    "status_weekly",
    "grid_week",
    "date",
    "total_duration_min",
    "activity_name",
    "activity_id",
    "athlete_jersey",
    "position_name",
    "team_name",
    "month_name",
    "day_name",
    "field_time",
    "total_distance",
    "peak_player_load",
    "total_player_load",
    "total_2d_player_load",
    "total_slow_player_load",
    "total_1d_fwd_player_load",
    "total_1d_side_player_load",
    "total_1d_up_player_load",
    "velocity_exertion",
    "max_vel",
    "peak_meta_power",
    "equivalent_distance",
    "meterage_per_minute",
    "Power Plays",
    "Impacts",
    "Hr Load",
    "Player Load Per Min",
    "Sprints Per Min",
    "Tags",
    "Split Name",
    "Sprint Distance (yards)",
    "sprint_distance_m",
    "source",
]


def locate_input_file() -> Path:
    """Return the preferred input path with fallback support."""
    if PRIMARY_INPUT.exists():
        return PRIMARY_INPUT
    if FALLBACK_INPUT.exists():
        print(f"Primary input missing; using fallback at {FALLBACK_INPUT}")
        return FALLBACK_INPUT
    raise FileNotFoundError(
        f"Neither {PRIMARY_INPUT} nor {FALLBACK_INPUT} exists. Cannot compute weekly status."
    )


def ensure_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Guarantee all expected columns exist."""
    missing = [col for col in columns if col not in df.columns]
    for col in missing:
        df[col] = pd.NA
    return df


def to_minutes_if_seconds(series: pd.Series) -> pd.Series:
    """Ensure field_time is in seconds (if already minutes, scale accordingly)."""
    numeric = pd.to_numeric(series, errors="coerce").fillna(0)
    if numeric.max() <= 600:  # heuristic: values <= 10 minutes probably still minutes
        return numeric * SECONDS_PER_MINUTE
    return numeric


def assign_weeks(df: pd.DataFrame) -> pd.DataFrame:
    """Compute grid_week values relative to START_WEEK."""
    df["grid_week"] = (
        ((df["date"] - START_WEEK).dt.days // 7) + 1
    )
    df = df[df["grid_week"] >= 1]

    current_week = ((pd.Timestamp.now().normalize() - START_WEEK).days // 7) + 1
    df = df[df["grid_week"] <= current_week]
    return df


def compute_status(df: pd.DataFrame) -> pd.DataFrame:
    """Flag athlete-days and athlete-weeks based on field time thresholds."""
    daily_seconds = (
        df.groupby(["athlete_name_full", "date"], dropna=False)["field_time"]
        .sum()
        .rename("daily_field_time_sec")
    )
    daily_status = (daily_seconds >= DAILY_ACTIVE_THRESHOLD).rename("status")

    weekly_seconds = (
        df.groupby(["athlete_name_full", "grid_week"], dropna=False)["field_time"]
        .sum()
        .rename("weekly_field_time_sec")
    )
    weekly_status = (weekly_seconds >= DAILY_ACTIVE_THRESHOLD).rename("status_weekly")

    df = df.join(daily_status, on=["athlete_name_full", "date"])
    df = df.join(weekly_status, on=["athlete_name_full", "grid_week"])
    df["status"] = df["status"].fillna(False).astype(bool)
    df["status_weekly"] = df["status_weekly"].fillna(False).astype(bool)
    return df


def main() -> None:
    input_path = locate_input_file()
    df = pd.read_csv(input_path)

    input_rows = len(df)
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    df = df[df["date"].notna()].copy()
    df["date"] = df["date"].dt.normalize()

    df["field_time"] = to_minutes_if_seconds(df.get("field_time"))
    df = assign_weeks(df)

    df = df.drop(columns=["status", "status_weekly"], errors="ignore")
    required_without_status = [
        col for col in COLUMN_ORDER if col not in {"status", "status_weekly"}
    ]
    df = ensure_columns(df, required_without_status)
    df = compute_status(df)
    df = ensure_columns(df, COLUMN_ORDER)

    df.sort_values(
        by=["grid_week", "athlete_name_full", "date"],
        ascending=[True, True, True],
        inplace=True,
        na_position="last",
    )
    df = df.reindex(columns=COLUMN_ORDER)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    date_min = df["date"].min()
    date_max = df["date"].max()
    unique_weeks = sorted(df["grid_week"].dropna().unique())

    weekly_unique = df.drop_duplicates(["athlete_name_full", "grid_week"])
    total_athlete_weeks = len(weekly_unique)
    athlete_weeks_status_true = int(weekly_unique["status"].sum())
    athlete_weeks_status_weekly_true = int(weekly_unique["status_weekly"].sum())

    if unique_weeks:
        first_week, last_week = unique_weeks[0], unique_weeks[-1]
    else:
        first_week = last_week = "N/A"

    print(f"Input rows processed: {input_rows}; usable rows: {len(df)}")
    print(f"Date range retained: {date_min} → {date_max}")
    print(f"Unique grid weeks: {len(unique_weeks)} (first={first_week}, last={last_week})")
    print(f"Total athlete-weeks: {total_athlete_weeks}")
    print(f"Athlete-weeks with status=True: {athlete_weeks_status_true}")
    print(
        f"Athlete-weeks with status_weekly=True: {athlete_weeks_status_weekly_true}"
    )


if __name__ == "__main__":
    main()
