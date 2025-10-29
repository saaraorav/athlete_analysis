#!/usr/bin/env python3
"""Compute average CMJ Peak Power / BM for game days with 7+ active athletes."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALIGNED_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_aligned_gamedays.csv"
PEAKPOWER_PATH = PROJECT_ROOT / "script" / "outputs" / "cmj_wsoc_peakpowerbm_wide.csv"
OUTPUT_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_game_day_peakpower.csv"

METRIC_COL = "Peak Power / BM"


def main() -> None:
    if not ALIGNED_PATH.exists():
        raise FileNotFoundError(f"Aligned game-day file not found at {ALIGNED_PATH}")
    if not PEAKPOWER_PATH.exists():
        raise FileNotFoundError(f"Peak power file not found at {PEAKPOWER_PATH}")

    aligned = pd.read_csv(ALIGNED_PATH)
    aligned["date"] = pd.to_datetime(aligned.get("date"), errors="coerce")
    aligned["athlete_name_full"] = aligned.get("athlete_name_full", "").astype(str).str.strip()
    aligned = aligned[aligned["date"].notna()].copy()

    aligned_active = aligned[aligned["status_weekly"].fillna(False)].copy()
    counts = (
        aligned_active.groupby(aligned_active["date"].dt.normalize())["athlete_name_full"]
        .nunique()
        .rename("active_athletes")
        .reset_index()
    )
    qualified_dates = counts[counts["active_athletes"] >= 7]
    print(
        f"Game days with status_weekly active athletes: {len(counts)} total; "
        f"{len(qualified_dates)} with >=7 active athletes."
    )

    peak_df = pd.read_csv(PEAKPOWER_PATH)
    if METRIC_COL not in peak_df.columns:
        raise KeyError(f"Expected metric column '{METRIC_COL}' in {PEAKPOWER_PATH}")
    peak_df["date"] = pd.to_datetime(peak_df.get("date"), errors="coerce")
    peak_df = peak_df[peak_df["date"].notna()].copy()

    merged = qualified_dates.merge(peak_df, on="date", how="left")
    if merged.empty:
        print("No matching CMJ entries found for qualified game days.")
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(OUTPUT_PATH, index=False)
        return

    result = (
        merged.groupby("date")
        .agg(
            active_athletes=("active_athletes", "first"),
            avg_peak_power=(METRIC_COL, "mean"),
            data_points=(METRIC_COL, "count"),
        )
        .reset_index()
        .sort_values("date")
    )
    result["date"] = result["date"].dt.strftime("%m/%d/%Y")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print(f"Summary rows written: {len(result)}")
    if not result.empty:
        print("Preview:")
        print(result.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
