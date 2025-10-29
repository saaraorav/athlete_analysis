#!/usr/bin/env python3
"""Aggregate weekly average meterage per minute for WSOC practices and games."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GAME_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_aligned_gamedays.csv"
PRACTICE_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_playertek_practice_only_with_status.csv"
OUTPUT_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_weekly_avg_meterage_by_event.csv"

START_WEEK = pd.Timestamp("2024-06-03")


def week_month_label(grid_week: int) -> str:
    """Return the month label for a given grid week using a majority-of-days rule."""
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


def load_and_aggregate(path: Path, label: str, *, group_by_date: bool) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found at {path}")

    df = pd.read_csv(path)
    total_rows = len(df)

    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    df["grid_week"] = pd.to_numeric(df.get("grid_week"), errors="coerce").astype("Int64")
    df["athlete_name_full"] = df.get("athlete_name_full", "").astype(str).str.strip()

    df = df[df["status_weekly"].fillna(False)].copy()
    filtered_rows = len(df)

    if group_by_date:
        grouped = (
            df.groupby(["grid_week", "date"], dropna=True)
            .agg(
                average_meterage_per_minute=("meterage_per_minute", "mean"),
                n_active_athletes=("athlete_name_full", "nunique"),
            )
            .reset_index()
        )
    else:
        grouped = (
            df.groupby("grid_week", dropna=True)
            .agg(
                average_meterage_per_minute=("meterage_per_minute", "mean"),
                n_active_athletes=("athlete_name_full", "nunique"),
            )
            .reset_index()
        )

    grouped["event"] = label
    grouped["month"] = grouped["grid_week"].astype(int).apply(week_month_label)
    grouped = grouped[
        ["event", "average_meterage_per_minute", "grid_week", "month", "n_active_athletes"]
    ]

    print(
        f"{label.capitalize()} input rows: {total_rows}; after status filter: {filtered_rows}; "
        f"records aggregated: {len(grouped)}"
    )

    return grouped


def main() -> None:
    game_rows = load_and_aggregate(GAME_PATH, "game", group_by_date=True)
    practice_rows = load_and_aggregate(PRACTICE_PATH, "practice", group_by_date=False)

    combined = pd.concat([game_rows, practice_rows], ignore_index=True, sort=False)
    combined.sort_values(by=["grid_week", "event"], inplace=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False)

    print(f"Combined rows written: {len(combined)}")
    if not combined.empty:
        print("First 5 rows:")
        print(combined.head(5).to_string(index=False))
        print("Last 5 rows:")
        print(combined.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
