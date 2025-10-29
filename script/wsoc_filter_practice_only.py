#!/usr/bin/env python3
"""Remove match days from practice-aligned WSOC data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PRACTICE_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_playertek_combined_aligned_practice.csv"
PRACTICE_OUTPUT_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_playertek_practice_only.csv"
STATUS_SOURCE_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_aligned_gamedays.csv"
FINAL_OUTPUT_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_playertek_practice_only_with_status.csv"
OPPONENT_PATH = PROJECT_ROOT / "raw_data" / "opponent_ranks copy.csv"
OUTPUT_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_playertek_practice_only.csv"
START_WEEK = pd.Timestamp("2024-06-03")


def load_practice() -> pd.DataFrame:
    if not SOURCE_PRACTICE_PATH.exists():
        raise FileNotFoundError(f"Practice-aligned data not found at {SOURCE_PRACTICE_PATH}")
    practice_df = pd.read_csv(SOURCE_PRACTICE_PATH)
    practice_df["date_obj"] = pd.to_datetime(practice_df.get("date"), errors="coerce")
    return practice_df


def load_game_dates() -> set[pd.Timestamp]:
    if not OPPONENT_PATH.exists():
        raise FileNotFoundError(f"Opponent schedule not found at {OPPONENT_PATH}")

    opp_df = pd.read_csv(OPPONENT_PATH)
    date_col = "date" if "date" in opp_df.columns else "Date" if "Date" in opp_df.columns else None
    if date_col is None:
        raise KeyError("Opponent file missing 'date' or 'Date' column.")

    opp_df["date_obj"] = pd.to_datetime(opp_df[date_col], errors="coerce")
    opp_df = opp_df[opp_df["date_obj"].notna()].copy()

    if "Team" not in opp_df.columns:
        raise KeyError("Opponent file missing 'Team' column for sport filtering.")
    opp_df = opp_df[opp_df["Team"].astype(str).str.casefold() == "soccer"].copy()

    soccer_dates = set(opp_df["date_obj"].dt.normalize())
    return soccer_dates


def main() -> None:
    practice_df = load_practice()
    soccer_game_dates = load_game_dates()

    pre_rows = len(practice_df)

    mask = practice_df["date_obj"].dt.normalize().isin(soccer_game_dates)
    filtered_df = practice_df[~mask].copy()

    post_rows = len(filtered_df)

    filtered_df["grid_week"] = (
        (filtered_df["date_obj"].dt.normalize() - START_WEEK).dt.days // 7
    ) + 1

    filtered_df.drop(columns=["date_obj"], inplace=True)

    PRACTICE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    filtered_df.to_csv(PRACTICE_OUTPUT_PATH, index=False)

    print(f"Practice rows before filtering: {pre_rows}")
    print(f"Practice rows after removing match days: {post_rows}")
    print(f"Removed rows (match days): {pre_rows - post_rows}")
    print(f"Unique soccer game dates removed: {len(soccer_game_dates)}")
    if post_rows:
        grid_min = filtered_df["grid_week"].min()
        grid_max = filtered_df["grid_week"].max()
        print(f"Grid week span in practice data: {grid_min} → {grid_max}")

    filtered_df.drop(columns=["grid_week"], inplace=True)

    enhance_with_status()


def enhance_with_status() -> None:
    if not PRACTICE_OUTPUT_PATH.exists():
        raise FileNotFoundError(f"Practice-only output not found at {PRACTICE_OUTPUT_PATH}")
    if not STATUS_SOURCE_PATH.exists():
        raise FileNotFoundError(f"Game-day status file not found at {STATUS_SOURCE_PATH}")

    practice_df = pd.read_csv(PRACTICE_OUTPUT_PATH)
    practice_df["date"] = pd.to_datetime(practice_df.get("date"), errors="coerce")
    practice_df["athlete_name_full"] = practice_df.get("athlete_name_full", "").astype(str).str.strip()
    practice_df = practice_df[practice_df["date"].notna()].copy()

    practice_df["grid_week"] = (
        (practice_df["date"].dt.normalize() - START_WEEK).dt.days // 7
    ) + 1

    status_df = pd.read_csv(STATUS_SOURCE_PATH)
    status_df["date"] = pd.to_datetime(status_df.get("date"), errors="coerce")
    status_df = status_df[status_df["date"].notna()].copy()
    status_df["athlete_name_full"] = status_df.get("athlete_name_full", "").astype(str).str.strip()

    if "status_weekly" not in status_df.columns:
        raise KeyError(
            "Status source file must contain 'status_weekly' column."
        )

    status_df = status_df.drop_duplicates(
        subset=["athlete_name_full", "grid_week"], keep="last"
    )[["athlete_name_full", "grid_week", "status_weekly"]]

    merged = practice_df.merge(
        status_df,
        on=["athlete_name_full", "grid_week"],
        how="left",
        suffixes=("", "_status"),
    )
    merged["status_weekly"] = merged["status_weekly"].fillna(False).astype(bool)

    columns = list(practice_df.columns)
    columns.append("status_weekly")
    merged = merged.reindex(columns=columns)

    merged.sort_values(
        by=["grid_week", "athlete_name_full", "date"],
        ascending=[False, True, False],
        inplace=True,
    )

    FINAL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(FINAL_OUTPUT_PATH, index=False)

    print(
        f"Practice rows with weekly status appended: {len(merged)} (saved to {FINAL_OUTPUT_PATH})"
    )


if __name__ == "__main__":
    main()
