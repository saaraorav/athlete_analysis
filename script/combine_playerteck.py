#!/usr/bin/env python3
"""Combine PlayerTek CSV exports and produce cleaned subsets."""

from pathlib import Path

import pandas as pd

DATE_FORMAT = "%m/%d/%Y"
YARDS_TO_METERS = 0.9144
MILES_TO_METERS = 1609.344
MPH_TO_MS = 0.44704
SECONDS_PER_MINUTE = 60
EXPECTED_COLUMNS = [
    "Date",
    "Session Title",
    "Player Name",
    "Split Name",
    "Tags",
    "Split Start Time",
    "Split End Time",
    "Duration",
    "Distance (miles)",
    "Sprint Distance (yards)",
    "Accelerations"
    "Power Plays",
    "Impacts",
    "Hr Load",
    "Top Speed (mph)",
    "Distance Per Min (yd/min)",
    "Power Score (w/kg)",
    "Max Deceleration (m/s/s)",
    "Max Acceleration (m/s/s)",
    "Player Load Per Min",
    "Player Load",
    "Sprints Per Min",
]
RENAMED_COLUMNS = {
    "Date": "date",
    "Player Name": "athlete_name",
    "Distance Per Min (yd/min)": "meterage_per_minute",  # converted to m/min after rename
    "Player Load": "total_player_load",
}
CATAPULT_EXPECTED_COLUMNS = [
    "athlete_name",
    "catapult_athlete_id",
    "date",
    "end_time",
    "activity_name",
    "athlete_weight",
    "activity_id",
    "athlete_jersey",
    "start_time",
    "position_name",
    "team_name",
    "month_name",
    "day_name",
    "field_time",
    "bench_time",
    "total_distance",
    "total_duration",
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
]
NAME_MAP = {
    "leah": "Leah Chancey",
    "kat": "Kat Lazor",
    "camille": "Camille Quarterman",
    "cat": "Catarina Albuquerque",
    "jules": "Jules Johnston",
    "kallie": "Kallie McKinney",
    "taylor": "Taylor Rish",
    "lauren": "Lauren Pickup",
    "dayo": "Dayo Tennyson",
    "mariana": "Mariana Elizondo",
    "carsyn": "Carsyn Martz",
    "kk": None,
    "gq": "Gabriela Quintero",
    "lilly": "Lilly Reuscher",
    "allie": "Allie Love",
    "sophie": "Sophie Zhang",
    "gorji": "Natalie Gorji",
    "mia": "Mia Brumlow",
    "betty": "Betty Velkova",
    "piper": "Piper Biziorek",
    "jess": "Jessica Molina",
    "claire": "Claire Tracy",
    "bailey": "Bailey Peek",
    "kenna": "Kenna Sanders",
    "jordyn": "Jordyn Mariam",
    "naija": "Naija Bruckner",
    "ally": "Allison Padron",
    "nat": "Natalie Gorji",
    "isabelle": "Isabelle Kent",
    "faith": "Faith Hutchins",
}
PLAYERTEK_ALIGNMENT_EXPECTED_COLUMNS = [
    "athlete_name",
    "date",
    "Session Title",
    "Split Start Time",
    "Split End Time",
    "Duration",
    "Distance (miles)",
    "Top Speed (mph)",
    "meterage_per_minute",
    "total_player_load",
    "Sprint Distance (yards)",
    "Power Plays",
    "Impacts",
    "Hr Load",
    "Player Load Per Min",
    "Sprints Per Min",
    "Tags",
    "Split Name",
]
UNIFIED_COLUMNS = [
    "athlete_name",
    "athlete_name_full",
    "athlete_name_unmatched",
    "catapult_athlete_id",
    "date",
    "end_time",
    "activity_name",
    "athlete_weight",
    "activity_id",
    "athlete_jersey",
    "start_time",
    "position_name",
    "team_name",
    "month_name",
    "day_name",
    "field_time",
    "bench_time",
    "total_distance",
    "total_duration_min",
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


def parse_date_column(series: pd.Series) -> pd.Series:
    """Parse PlayerTek date column that may be Excel serials or strings."""
    numeric_dates = pd.to_numeric(series, errors="coerce")
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    numeric_mask = numeric_dates.notna()
    if numeric_mask.any():
        parsed.loc[numeric_mask] = pd.to_datetime(
            numeric_dates.loc[numeric_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

    remaining_mask = parsed.isna()
    if remaining_mask.any():
        parsed.loc[remaining_mask] = pd.to_datetime(
            series.loc[remaining_mask].astype(str).str.strip(),
            errors="coerce",
            infer_datetime_format=True,
        )

    return parsed


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    input_dir = project_root / "raw_playerteck_wsoccer"
    output_path = project_root / "script" / "outputs" / "playerteck_combined_clean.csv"

    if not input_dir.exists():
        print(f"Input directory {input_dir} does not exist. Nothing to do.")
        return

    csv_files = sorted(input_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {input_dir}. Nothing to do.")
        return

    combined_frames = []
    missing_columns_overall: set[str] = set()
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        df = df.copy()  # avoid SettingWithCopy warnings downstream

        if "Date" in df.columns:
            original_dates = df["Date"].copy()
            parsed_dates = parse_date_column(original_dates)
            df["_parsed_date"] = parsed_dates
            df["Date"] = parsed_dates.dt.strftime(DATE_FORMAT)

            missing_mask = df["_parsed_date"].isna()
            if missing_mask.any():
                df.loc[missing_mask, "Date"] = original_dates.loc[missing_mask].astype(str)
                missing_count = int(missing_mask.sum())
                print(f"Warning: {missing_count} rows in {csv_file.name} have unparsed dates.")
        else:
            df["_parsed_date"] = pd.NaT
            print(f"Warning: 'Date' column missing in {csv_file.name}.")

        missing_in_file = [col for col in EXPECTED_COLUMNS if col not in df.columns]
        if missing_in_file:
            missing_columns_overall.update(missing_in_file)

        selected = df.reindex(columns=EXPECTED_COLUMNS)
        selected["_parsed_date"] = df["_parsed_date"]
        combined_frames.append(selected)

    combined_df = pd.concat(combined_frames, ignore_index=True, sort=False)

    combined_df.sort_values(
        by="_parsed_date",
        ascending=False,
        na_position="last",
        inplace=True,
    )
    combined_df.drop(columns="_parsed_date", inplace=True)
    combined_df.rename(columns=RENAMED_COLUMNS, inplace=True)
    if "meterage_per_minute" in combined_df.columns:
        combined_df["meterage_per_minute"] = (
            pd.to_numeric(combined_df["meterage_per_minute"], errors="coerce") * YARDS_TO_METERS
        )
    filter_column = None
    if "Split Name" in combined_df.columns:
        filter_column = "Split Name"
    elif "Tags" in combined_df.columns:
        filter_column = "Tags"

    if filter_column:
        normalized = (
            combined_df[filter_column].astype(str).str.strip().str.lower()
        )
        tag_mask = normalized.eq("game")

        if filter_column == "Split Name":
            date_series = combined_df["date"] if "date" in combined_df.columns else combined_df.get("Date")
            if date_series is not None:
                special_mask = (
                    date_series.astype(str).str.strip().eq("08/15/2024")
                    & normalized.eq("all")
                )
                tag_mask = tag_mask | special_mask

        before_rows = len(combined_df)
        combined_df = combined_df[tag_mask].copy()
        print(
            f"PlayerTek filter: retained {combined_df.shape[0]} of {before_rows} rows based on {filter_column} filter."
        )
    else:
        print("PlayerTek filter: neither 'Split Name' nor 'Tags' column present; no filtering applied.")

    removal_names = {"kenna", "mia", "isabelle", "betty", "claire", "jess", "jordyn"}
    name_column = None
    if "athlete_name_full" in combined_df.columns:
        name_column = "athlete_name_full"
    elif "athlete_name" in combined_df.columns:
        name_column = "athlete_name"

    if name_column:
        name_norm = combined_df[name_column].astype(str).str.strip().str.lower()
        remove_mask = name_norm.isin(removal_names)
        if remove_mask.any():
            before_remove = len(combined_df)
            combined_df = combined_df[~remove_mask].copy()
            removed_count = before_remove - len(combined_df)
            print(
                f"PlayerTek filter: removed {removed_count} rows for excluded athletes: {sorted(removal_names)}"
            )
    else:
        print("PlayerTek filter: athlete name column missing; no name-based exclusions applied.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path, index=False)

    if missing_columns_overall:
        missing_list = ", ".join(sorted(missing_columns_overall))
        print(f"Warning: Missing expected columns across files: {missing_list}")

    print(f"Processed {len(csv_files)} files from {input_dir}.")
    print(f"Columns retained: {list(combined_df.columns)}")
    print(f"Final dataset shape: {combined_df.shape[0]} rows x {combined_df.shape[1]} columns")

    process_catapult_dataset(project_root)
    align_playertek_catapult_outputs(project_root)


def process_catapult_dataset(project_root: Path) -> None:
    catapult_path = project_root / "raw_data" / "tblCatapultWSOCStatsByActivity.csv"
    output_path = project_root / "script" / "outputs" / "wsoc_catapult_subset.csv"

    if not catapult_path.exists():
        print(f"Catapult file not found at {catapult_path}. Skipping.")
        return

    print(f"Catapult file found at {catapult_path}.")

    df = pd.read_csv(catapult_path)
    df = df.copy()

    missing_columns = [col for col in CATAPULT_EXPECTED_COLUMNS if col not in df.columns]

    if "activity_name" in df.columns:
        activity_mask = df["activity_name"].astype(str).str.startswith("Activity", na=False)
        removed = int(activity_mask.sum())
        if removed:
            print(f"Catapult info: Removing {removed} rows with activity_name starting with 'Activity'.")
        df = df.loc[~activity_mask].copy()

    parsed_dates = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    if "date" in df.columns:
        parsed_dates = pd.to_datetime(df["date"], errors="coerce")

    subset = df.reindex(columns=CATAPULT_EXPECTED_COLUMNS)
    subset["_parsed_date"] = parsed_dates
    subset.sort_values(
        by="_parsed_date",
        ascending=False,
        na_position="last",
        inplace=True,
    )
    subset.drop(columns="_parsed_date", inplace=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subset.to_csv(output_path, index=False)

    if missing_columns:
        missing_list = ", ".join(missing_columns)
        print(f"Catapult warning: Missing expected columns: {missing_list}")

    non_na_dates = subset["date"].dropna() if "date" in subset.columns else pd.Series(dtype="object")
    first_date = non_na_dates.iloc[0] if not non_na_dates.empty else "N/A"
    last_date = non_na_dates.iloc[-1] if not non_na_dates.empty else "N/A"

    print(f"Catapult dataset shape: {subset.shape[0]} rows x {subset.shape[1]} columns")
    print(f"Catapult date range: first={first_date}, last={last_date}")


def align_playertek_catapult_outputs(project_root: Path) -> None:
    playertek_path = project_root / "script" / "outputs" / "playerteck_combined_clean.csv"
    catapult_path = project_root / "script" / "outputs" / "wsoc_catapult_subset.csv"
    output_path = project_root / "script" / "outputs" / "wsoc_playertek_combined_aligned.csv"

    missing_files = []
    if not catapult_path.exists():
        missing_files.append(str(catapult_path))
    if not playertek_path.exists():
        missing_files.append(str(playertek_path))
    if missing_files:
        missing_list = "; ".join(missing_files)
        print(f"Alignment skipped: required file(s) missing - {missing_list}")
        return

    catapult_df = pd.read_csv(catapult_path)
    playertek_df = pd.read_csv(playertek_path)

    if "Tags" in playertek_df.columns:
        pre_filter_rows = len(playertek_df)
        playertek_df = playertek_df[
            playertek_df["Tags"].astype(str).str.strip().str.lower() == "game"
        ].copy()
        print(
            f"Alignment info: filtered PlayerTek rows for Tags == 'game'; "
            f"{len(playertek_df)} of {pre_filter_rows} rows retained."
        )
    else:
        print("Alignment warning: PlayerTek data missing 'Tags' column; no game filter applied.")

    catapult_missing = [col for col in CATAPULT_EXPECTED_COLUMNS if col not in catapult_df.columns]
    playertek_missing = [col for col in PLAYERTEK_ALIGNMENT_EXPECTED_COLUMNS if col not in playertek_df.columns]

    conversions: list[str] = []

    playertek_df = playertek_df.copy()
    playertek_rename_map = {
        "Session Title": "activity_name",
        "Split Start Time": "start_time",
        "Split End Time": "end_time",
        "total_player_load": "total_player_load",
        "meterage_per_minute": "meterage_per_minute",
    }
    playertek_df.rename(columns=playertek_rename_map, inplace=True)

    if "Top Speed (mph)" in playertek_df.columns:
        playertek_df["max_vel"] = (
            pd.to_numeric(playertek_df["Top Speed (mph)"], errors="coerce") * MPH_TO_MS
        )
        conversions.append("Converted PlayerTek Top Speed (mph) to max_vel (m/s)")
    playertek_df.drop(columns=["Top Speed (mph)"], inplace=True, errors="ignore")

    if "Distance (miles)" in playertek_df.columns:
        playertek_df["total_distance"] = (
            pd.to_numeric(playertek_df["Distance (miles)"], errors="coerce") * MILES_TO_METERS
        )
        conversions.append("Converted PlayerTek Distance (miles) to total_distance (m)")
    playertek_df.drop(columns=["Distance (miles)"], inplace=True, errors="ignore")

    if "Duration" in playertek_df.columns:
        playertek_duration = pd.to_numeric(playertek_df["Duration"], errors="coerce")
        conversions.append("PlayerTek Duration copied to total_duration_min/field_time (min)")
    else:
        playertek_duration = pd.Series(index=playertek_df.index, dtype="float64")
    playertek_df["total_duration_min"] = playertek_duration
    playertek_df["field_time"] = playertek_duration
    playertek_df.drop(columns=["Duration"], inplace=True, errors="ignore")

    if "Sprint Distance (yards)" in playertek_df.columns:
        playertek_df["sprint_distance_m"] = (
            pd.to_numeric(playertek_df["Sprint Distance (yards)"], errors="coerce") * YARDS_TO_METERS
        )
        conversions.append("Converted PlayerTek Sprint Distance (yards) to sprint_distance_m (m)")
    else:
        playertek_df["sprint_distance_m"] = pd.Series(
            index=playertek_df.index, dtype="float64"
        )

    if "meterage_per_minute" in playertek_df.columns:
        playertek_df["meterage_per_minute"] = pd.to_numeric(
            playertek_df["meterage_per_minute"], errors="coerce"
        )
    else:
        playertek_df["meterage_per_minute"] = pd.Series(
            index=playertek_df.index, dtype="float64"
        )
    if "total_distance" not in playertek_df.columns:
        playertek_df["total_distance"] = pd.Series(index=playertek_df.index, dtype="float64")
    if "max_vel" not in playertek_df.columns:
        playertek_df["max_vel"] = pd.Series(index=playertek_df.index, dtype="float64")
    if "field_time" not in playertek_df.columns:
        playertek_df["field_time"] = pd.Series(index=playertek_df.index, dtype="float64")

    playertek_df["date"] = pd.to_datetime(playertek_df.get("date"), errors="coerce")
    playertek_df["athlete_name_lower"] = (
        playertek_df["athlete_name"].astype(str).str.strip().str.lower()
    )
    mapped_names = playertek_df["athlete_name_lower"].map(NAME_MAP)
    matched_mask = mapped_names.notna()
    unmatched_mask = ~matched_mask

    playertek_df["athlete_name_full"] = playertek_df["athlete_name"]
    playertek_df.loc[matched_mask, "athlete_name_full"] = mapped_names.loc[matched_mask]
    playertek_df["athlete_name_unmatched"] = pd.Series(
        index=playertek_df.index, dtype="object"
    )
    playertek_df.loc[unmatched_mask, "athlete_name_unmatched"] = playertek_df.loc[
        unmatched_mask, "athlete_name"
    ]
    matched_unique = int(mapped_names[matched_mask].nunique())
    unmatched_unique = int(playertek_df.loc[unmatched_mask, "athlete_name_lower"].nunique())

    unmatched_names_df = (
        playertek_df.loc[unmatched_mask, ["athlete_name", "athlete_name_lower"]]
        .drop_duplicates()
        .sort_values(by="athlete_name_lower")
    )
    unmatched_output_path = project_root / "script" / "outputs" / "playertek_unmatched_names.csv"
    unmatched_output_path.parent.mkdir(parents=True, exist_ok=True)
    unmatched_names_df.to_csv(unmatched_output_path, index=False)
    unmatched_list = unmatched_names_df["athlete_name"].tolist()
    print(
        f"PlayerTek name standardization: matched {matched_unique} unique athletes; "
        f"unmatched {unmatched_unique}."
    )
    if unmatched_list:
        print(f"Unmatched PlayerTek athletes: {unmatched_list}")
    else:
        print("Unmatched PlayerTek athletes: none.")
    playertek_df.drop(columns=["athlete_name_lower"], inplace=True)

    playertek_df["source"] = "playertek"

    catapult_df = catapult_df.copy()
    catapult_df["date"] = pd.to_datetime(catapult_df.get("date"), errors="coerce")
    catapult_df["athlete_name_full"] = catapult_df["athlete_name"]
    catapult_df["athlete_name_unmatched"] = pd.Series(
        index=catapult_df.index, dtype="object"
    )
    if "total_duration" in catapult_df.columns:
        catapult_duration = pd.to_numeric(catapult_df["total_duration"], errors="coerce")
        catapult_df["total_duration_min"] = catapult_duration / SECONDS_PER_MINUTE
        conversions.append("Converted Catapult total_duration (s) to total_duration_min (min)")
    else:
        catapult_df["total_duration_min"] = pd.Series(
            index=catapult_df.index, dtype="float64"
        )
    catapult_df.drop(columns=["total_duration"], inplace=True, errors="ignore")

    if "Sprint Distance (yards)" not in catapult_df.columns:
        catapult_df["Sprint Distance (yards)"] = pd.Series(
            index=catapult_df.index, dtype="float64"
        )
    catapult_df["sprint_distance_m"] = pd.Series(index=catapult_df.index, dtype="float64")
    if "field_time" not in catapult_df.columns:
        catapult_df["field_time"] = pd.Series(index=catapult_df.index, dtype="float64")
    catapult_df["source"] = "catapult"

    catapult_aligned = catapult_df.reindex(columns=UNIFIED_COLUMNS)
    playertek_aligned = playertek_df.reindex(columns=UNIFIED_COLUMNS)

    combined_df = pd.concat(
        [catapult_aligned, playertek_aligned],
        ignore_index=True,
        sort=False,
    )
    combined_df.sort_values(
        by="date",
        ascending=False,
        na_position="last",
        inplace=True,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path, index=False)

    print(
        f"Source counts - catapult: {len(catapult_aligned)}, "
        f"playertek: {len(playertek_aligned)}"
    )
    print(
        f"Name mapping summary: {matched_unique} matched unique PlayerTek athletes; "
        f"{unmatched_unique} unmatched."
    )
    if catapult_missing:
        print(f"Alignment warning: Catapult missing columns: {', '.join(catapult_missing)}")
    else:
        print("Alignment info: Catapult input contained all expected columns.")
    if playertek_missing:
        print(f"Alignment warning: PlayerTek missing columns: {', '.join(playertek_missing)}")
    else:
        print("Alignment info: PlayerTek input contained all expected columns.")

    conversions_msg = "; ".join(conversions) if conversions else "None"
    print(f"Unit conversions applied: {conversions_msg}")

    non_na_dates = combined_df["date"].dropna()
    if not non_na_dates.empty:
        first_date = non_na_dates.max()
        last_date = non_na_dates.min()
        first_str = first_date.strftime(DATE_FORMAT)
        last_str = last_date.strftime(DATE_FORMAT)
    else:
        first_str = last_str = "N/A"

    print(
        f"Aligned dataset shape: {combined_df.shape[0]} rows x {combined_df.shape[1]} columns; "
        f"date range {first_str} to {last_str}"
    )


if __name__ == "__main__":
    main()
