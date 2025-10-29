#!/usr/bin/env python3
"""Filter aligned WSOC performance data to scheduled game days."""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALIGNED_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_weekly_with_status.csv"
OPPONENT_PATH = PROJECT_ROOT / "raw_data" / "opponent_ranks copy.csv"
OUTPUT_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_aligned_gamedays.csv"

DATE_FMT = "%m/%d/%Y"


def load_opponents() -> pd.DataFrame:
    if not OPPONENT_PATH.exists():
        raise FileNotFoundError(f"Opponent schedule not found at {OPPONENT_PATH}")

    opp_df = pd.read_csv(OPPONENT_PATH)

    date_col = "date" if "date" in opp_df.columns else "Date" if "Date" in opp_df.columns else None
    if date_col is None:
        raise KeyError("Opponent file missing expected 'date' or 'Date' column.")

    opp_df["date_obj"] = pd.to_datetime(opp_df[date_col], errors="coerce")
    opp_df = opp_df[opp_df["date_obj"].notna()].copy()

    opp_df["date"] = opp_df["date_obj"].dt.strftime(DATE_FMT)

    if "Team" not in opp_df.columns:
        raise KeyError("Opponent file missing 'Team' column for sport filtering.")
    opp_df = opp_df[opp_df["Team"].astype(str).str.strip().str.casefold() == "soccer"].copy()

    keep_cols = ["date"]
    potential_context = ["Opponent", "Location", "Result", "Rank", "Notes"]
    keep_cols.extend([col for col in potential_context if col in opp_df.columns])

    opp_df = opp_df[keep_cols].drop_duplicates(subset="date", keep="first")
    return opp_df


def load_aligned() -> pd.DataFrame:
    if not ALIGNED_PATH.exists():
        raise FileNotFoundError(f"Aligned performance file not found at {ALIGNED_PATH}")
    aligned_df = pd.read_csv(ALIGNED_PATH)
    aligned_df["date_obj"] = pd.to_datetime(aligned_df.get("date"), errors="coerce")
    aligned_df = aligned_df[aligned_df["date_obj"].notna()].copy()
    aligned_df["date"] = aligned_df["date_obj"].dt.strftime(DATE_FMT)
    return aligned_df


def main() -> None:
    opp_df = load_opponents()
    aligned_df = load_aligned()

    pre_rows = len(aligned_df)
    joined_df = aligned_df.merge(opp_df, on="date", how="inner", suffixes=("", "_opponent"))

    post_rows = len(joined_df)
    unique_dates = sorted(joined_df["date"].unique())

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joined_df.to_csv(OUTPUT_PATH, index=False)

    earliest = unique_dates[0] if unique_dates else "N/A"
    latest = unique_dates[-1] if unique_dates else "N/A"

    print(f"Aligned rows before filter: {pre_rows}")
    print(f"Aligned rows after matching opponent dates: {post_rows}")
    print(f"Distinct opponent game dates: {len(unique_dates)}")
    print(f"Game date range: {earliest} → {latest}")
    print("Sample joined rows:")
    print(joined_df.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
