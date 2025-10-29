#!/usr/bin/env python3
"""Plot weekly CMJ peak power alongside game and practice meterage."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
METERAGE_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_weekly_avg_meterage_by_event.csv"
GAME_ALIGNED_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_aligned_gamedays.csv"
PEAK_PATH = PROJECT_ROOT / "script" / "outputs" / "wsoc_game_day_peakpower.csv"
PLOT_DIR = PROJECT_ROOT / "script" / "plots"

ANCHOR_DATE = pd.Timestamp("2024-06-03")
YEARS = [2024, 2025]
RECESS_WINDOWS = {
    2024: [(7, 9)],
    2025: [(7, 9)],
}

RED_ZONE = {
    2024: [(8, 10)],
    2025: [(4, 7)],
}

def assign_grid_week(dates: pd.Series) -> pd.Series:
    return ((dates - ANCHOR_DATE).dt.days // 7) + 1


def week_month_label(grid_week: int) -> str:
    monday = ANCHOR_DATE + pd.Timedelta(weeks=grid_week - 1)
    week_days = pd.date_range(monday, periods=7, freq="D")
    counts = week_days.to_period("M").value_counts()
    max_count = counts.max()
    candidate_periods = counts[counts == max_count].index.tolist()
    monday_period = monday.to_period("M")
    chosen = monday_period if monday_period in candidate_periods else sorted(candidate_periods)[0]
    return chosen.to_timestamp().strftime("%b %Y")


def compute_cmj_weekly() -> pd.DataFrame:
    peak_df = pd.read_csv(PEAK_PATH)
    peak_df["date"] = pd.to_datetime(peak_df.get("date"), errors="coerce")
    peak_df = peak_df[peak_df["date"].notna()].copy()
    peak_df["grid_week"] = assign_grid_week(peak_df["date"])

    if "avg_peak_power" not in peak_df.columns:
        raise KeyError("Expected column 'avg_peak_power' in wsoc_game_day_peakpower.csv")

    cmj = peak_df[["grid_week", "avg_peak_power"]].copy()
    cmj = cmj.rename(columns={"avg_peak_power": "cmj_peak_power"})
    cmj["week_start"] = ANCHOR_DATE + pd.to_timedelta(cmj["grid_week"] - 1, unit="W")
    cmj["year"] = cmj["week_start"].dt.year
    return cmj


def compute_practice_meterage() -> pd.DataFrame:
    meter_df = pd.read_csv(METERAGE_PATH)
    meter_df = meter_df[meter_df["event"].str.lower() == "practice"].copy()
    grouped = (
        meter_df.groupby("grid_week", dropna=True)
        .agg(
            average_meterage_per_minute=("average_meterage_per_minute", "mean"),
            n_active_athletes=("n_active_athletes", "max"),
        )
        .reset_index()
    )
    grouped["event"] = "practice"
    grouped["week_start"] = ANCHOR_DATE + pd.to_timedelta(grouped["grid_week"] - 1, unit="W")
    grouped["year"] = grouped["week_start"].dt.year
    grouped["month"] = grouped["grid_week"].astype(int).apply(week_month_label)
    grouped["date"] = pd.NaT
    return grouped


def compute_game_meterage() -> pd.DataFrame:
    game_df = pd.read_csv(GAME_ALIGNED_PATH)
    game_df["date"] = pd.to_datetime(game_df.get("date"), errors="coerce")
    game_df = game_df[game_df["date"].notna()].copy()
    game_df["grid_week"] = assign_grid_week(game_df["date"])
    game_df = game_df[game_df["status_weekly"].fillna(False)].copy()
    game_df["athlete_key"] = game_df.get("athlete_name_full", "").astype(str).str.strip()

    grouped = (
        game_df.groupby(["grid_week", "date"], dropna=True)
        .agg(
            average_meterage_per_minute=("meterage_per_minute", "mean"),
            n_active_athletes=("athlete_key", "nunique"),
        )
        .reset_index()
    )
    grouped["event"] = "game"
    grouped["week_start"] = ANCHOR_DATE + pd.to_timedelta(grouped["grid_week"] - 1, unit="W")
    grouped["year"] = grouped["week_start"].dt.year
    grouped["month"] = grouped["grid_week"].astype(int).apply(week_month_label)
    return grouped


def school_week_ticks(year: int, start_week: int, end_week: int) -> pd.DataFrame:
    data = {
        "label": [f"Week {week}" for week in range(1, end_week - start_week + 2)],
        "grid_week": list(range(start_week, end_week + 1)),
    }
    return pd.DataFrame(data)


def plot_year(
    cmj_df: pd.DataFrame,
    practice_df: pd.DataFrame,
    game_df: pd.DataFrame,
    year: int,
    output_path: Path,
    cmj_limits: tuple[float, float] | None,
    meter_limits: tuple[float, float] | None,
) -> None:
    cmj_year = cmj_df.copy()
    practice_year = practice_df.copy()
    game_year = game_df.copy()

    start_date = pd.Timestamp(year=year, month=7, day=1)
    end_date = pd.Timestamp(year=year, month=12, day=31)

    cmj_year = cmj_year[(cmj_year["week_start"] >= start_date) & (cmj_year["week_start"] <= end_date)]
    practice_year = practice_year[
        (practice_year["week_start"] >= start_date) & (practice_year["week_start"] <= end_date)
    ]
    game_year = game_year[(game_year["week_start"] >= start_date) & (game_year["week_start"] <= end_date)]

    if cmj_year.empty and practice_year.empty and game_year.empty:
        print(f"No data available for {year}; skipping plot.")
        return

    fig, ax_left = plt.subplots(figsize=(12, 6))
    ax_right = ax_left.twinx()

    if not cmj_year.empty:
        offsets = []
        for _, grp in cmj_year.groupby("grid_week"):
            n = len(grp)
            if n == 1:
                offsets.append(0.0)
            elif n == 2:
                offsets.extend([0, 0.6])
            else:
                span = 0.2
                extras = np.linspace(-span, span, n)
                offsets.extend(extras)
        cmj_year = cmj_year.assign(x_offset=offsets)
        ax_left.scatter(
            cmj_year["grid_week"] + cmj_year["x_offset"],
            cmj_year["cmj_peak_power"],
            color="black",
            label="CMJ Peak Power/BM",
            zorder=7,
        )
        if cmj_limits:
            ax_left.set_ylim(cmj_limits)

    if not practice_year.empty:
        ax_right.scatter(
            practice_year["grid_week"],
            practice_year["average_meterage_per_minute"],
            color="red",
            label="Practice meterage",
            zorder=5,
        )

    if not game_year.empty:
        offsets = []
        for _, grp in game_year.groupby("grid_week"):
            n = len(grp)
            if n == 1:
                offsets.append(0.0)
            elif n == 2:
                offsets.extend([0.0, 0.6])
            else:
                extras = [0.6 * (i + 1) for i in range(n - 1)]
                offsets.extend([0.0] + extras)
        game_year = game_year.assign(x_offset=offsets)
        ax_right.scatter(
            game_year["grid_week"] + game_year["x_offset"],
            game_year["average_meterage_per_minute"],
            color="blue",
            edgecolors="black",
            label="Game meterage",
            zorder=6,
        )

    if meter_limits:
        ax_right.set_ylim(meter_limits)

    combined_counts = pd.concat([practice_year, game_year], ignore_index=True, sort=False)
    max_counts = pd.DataFrame(columns=["grid_week", "n_active_athletes"])
    if not combined_counts.empty:
        max_counts = (
            combined_counts.groupby("grid_week")["n_active_athletes"].max().reset_index()
        )

    # Later: annotate on top of axis

    all_weeks = sorted(
        set(cmj_year["grid_week"].tolist())
        | set(practice_year["grid_week"].tolist())
        | set(game_year["grid_week"].tolist())
    )

    if year == 2024:
        school_start = pd.Timestamp("2024-08-26")
    else:
        school_start = pd.Timestamp("2025-08-25")

    school_start_week = int(assign_grid_week(pd.Series([school_start])).iloc[0])

    for start, end in RECESS_WINDOWS.get(year, []):
        start_idx = int(start)
        end_idx = int(end)
        start_grid = school_start_week + (start_idx - 1)
        end_grid = school_start_week + (end_idx - 1)
        ax_left.axvspan(start_grid, end_grid + 1, color="lightgreen", alpha=0.2)

    for start, end in RED_ZONE.get(year, []):
        start_idx = int(start)
        end_idx = int(end)
        start_grid = school_start_week + (start_idx - 1)
        end_grid = school_start_week + (end_idx - 1)
        ax_left.axvspan(start_grid, end_grid + 1, color="red", alpha=0.2)

    def week_label(grid_week: int) -> str:
        offset = grid_week - school_start_week
        if offset < 0:
            return f"T{offset}"
        return f"W{offset + 1}"

    if all_weeks:
        tick_weeks = all_weeks
        tick_labels = [week_label(int(w)) for w in tick_weeks]
        ax_left.set_xticks(tick_weeks)
        ax_left.set_xticklabels(tick_labels, rotation=45, ha="right")
        if not max_counts.empty:
            for _, row in max_counts.iterrows():
                grid_week = row["grid_week"]
                count = row["n_active_athletes"]
                ax_left.text(
                    grid_week,
                    1.02,
                    str(count),
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    color="black",
                    transform=ax_left.get_xaxis_transform(which="grid"),
                    clip_on=False,
                )

    ax_left.text(0.5, 1.08, "Number of Active Athletes per Week",
             transform=ax_left.transAxes, ha="center", va="bottom", fontsize=11)
    ax_left.tick_params(axis="x", labeltop=False, labelbottom=True)
    ax_left.set_xlabel("Week of School")
    ax_left.set_ylabel("Peak Power / BM")
    ax_right.set_ylabel("Meterage per minute")
    title = f"WSOC Weekly – {year}"
    fig.suptitle(title, fontsize=14, fontweight="bold")
    ax_left.grid(True, which="both", linestyle="--", alpha=0.3)

    for week in all_weeks:
        ax_left.axvline(week, color="gray", linestyle=":", linewidth=0.5, alpha=0.5)

    handles_left, labels_left = ax_left.get_legend_handles_labels()
    handles_right, labels_right = ax_right.get_legend_handles_labels()
    ax_left.legend(handles_left + handles_right, labels_left + labels_right, loc="upper left")

    candidates = []
    if not cmj_year.empty:
        candidates.extend(cmj_year["grid_week"].tolist())
    if not combined_counts.empty:
        candidates.extend(combined_counts["grid_week"].tolist())
    if candidates:
        ax_left.set_xlim(min(candidates) - 0.5, max(candidates) + 0.5)

    fig.tight_layout(rect=[0, 0.12, 1, 0.92])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    cmj_range = (
        (cmj_year["cmj_peak_power"].min(), cmj_year["cmj_peak_power"].max())
        if not cmj_year.empty
        else (None, None)
    )
    meter_records = len(practice_year) + len(game_year)
    print(f"{title}: CMJ range {cmj_range}; cmj weeks={len(cmj_year)}, meterage records={meter_records}")
    if all_weeks:
        sample_ticks = list(zip(tick_weeks, tick_labels))[:5]
        print("Week label sample:", sample_ticks)


def main() -> None:
    cmj_weekly = compute_cmj_weekly()
    practice_weekly = compute_practice_meterage()
    game_meterage = compute_game_meterage()

    cmj_limits = (45, 60)

    meter_limits = None
    combined_meter = pd.concat([practice_weekly, game_meterage], ignore_index=True, sort=False)
    if not combined_meter.empty:
        meter_min = combined_meter["average_meterage_per_minute"].min()
        meter_max = combined_meter["average_meterage_per_minute"].max()
        padding = 0.02 * (meter_max - meter_min if meter_max != meter_min else abs(meter_min) or 1.0)
        meter_limits = (meter_min - padding, meter_max + padding)

    for year in YEARS:
        output_path = PLOT_DIR / f"wsoc_weekly_ppbm_meterage_{year}.png"
        plot_year(cmj_weekly, practice_weekly, game_meterage, year, output_path, cmj_limits, meter_limits)


if __name__ == "__main__":
    main()
