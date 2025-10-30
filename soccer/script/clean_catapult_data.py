# from matplotlib.pylab import NaN
import pandas as pd
import numpy as np
from pathlib import Path

# --- Folder path ---
folder = Path("../raw_playerteck_wsoccer")

all_files = sorted(folder.glob("*.csv"))

# Combine all raw playerteck files into one DataFrame
combined_playerteck = pd.concat(
    [pd.read_csv(f) for f in all_files],
    ignore_index=True
)

combined_playerteck["Date"] = pd.to_datetime(
    combined_playerteck["Date"],
    unit="D",
    origin="1899-12-30"
)

# --- Format Excel time as MM/DD/YYYY ---
combined_playerteck["Date"] = combined_playerteck["Date"].dt.strftime("%m/%d/%Y")

# print(combined_df.head(200))

# --- Keep and rename relevant columns ---
EXPECTED_COLUMNS = [
    "Date",
    "Session Title",
    "Player Name",
    "Split Name",
    "Tags",
    "Duration",
    "Distance Per Min (yd/min)",
    "Player Load Per Min",
    "Player Load",
]

RENAMED_COLUMNS = {
    "Date": "date",
    "Player Name": "athlete_name",
    "Duration": "total_duration",
    "Distance Per Min (yd/min)": "meterage_per_minute",  # converted to m/min after rename
    "Player Load": "total_player_load",
    "Session Title": "activity_name",
    "Split Name": "split_name",
    "Tags": "tags",
    "Player Load Per Min": "player_load_per_min",
}


combined_playerteck = combined_playerteck[EXPECTED_COLUMNS].copy()

# --- Rename selected columns ---
combined_playerteck = combined_playerteck.rename(columns=RENAMED_COLUMNS)

# convert Distance from yards/min to meters/min ---
if "meterage_per_minute" in combined_playerteck.columns:
    combined_playerteck["meterage_per_minute"] = combined_playerteck["meterage_per_minute"] * 0.9144 # yards to meters

# print(combined_df.head(200))
# output_path = "../clean_data/playerteck_raw.csv"
# combined_playerteck.to_csv(output_path, index=False)
# print(f"Saved merged file to: {output_path}")

# unique_tags = combined_df["Tags"].dropna().unique()
# print(unique_tags)

# MAP NAMES for playerteck data
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
    "kk": "Mikala Furuto",
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

# --- Make lowercase copy for matching ---
combined_playerteck["athlete_name_mapped"] = (
    combined_playerteck["athlete_name"]
    .astype(str)
    .str.strip()
    .str.lower()
    .replace(NAME_MAP)
)

# --- Prefer mapped name if available, else original ---
combined_playerteck["athlete_name"] = combined_playerteck["athlete_name_mapped"].combine_first(combined_playerteck["athlete_name"])

# --- Clean up: drop helper column ---
combined_df = combined_playerteck.drop(columns=["athlete_name_mapped"])

# --- Optional: fix capitalization for any remaining lowercase names ---
combined_df["athlete_name"] = combined_df["athlete_name"].str.title()
combined_df["date"] = pd.to_datetime(combined_df["date"], errors="coerce")

# Sort descending by date (most recent → oldest)
merged_df = combined_df.sort_values("date", ascending=False).reset_index(drop=True)

# output_path = "../clean_data/playerteck_raw.csv"
# combined_playerteck.to_csv(output_path, index=False)
# print(f"Saved merged file to: {output_path}")

# COMBINE PLAYERTECK AND CATAPULT DATA
# need to be inside soccer/script folder to run correctly
raw_catapult_data = pd.read_csv("../raw_data/tblCatapultWSOCStatsByActivity.csv")

game_day_data = pd.read_csv("../raw_data/opponent_ranks.csv")

# List of columns to keep
cols_to_keep = ['date', 'athlete_name', 'catapult_athlete_id', 'activity_name','month_name', 'total_duration', 'total_player_load', 'meterage_per_minute']
raw_catapult_data['date'] = pd.to_datetime(raw_catapult_data['date'], format='%m/%d/%Y')

# Filter columns, date, and sort
raw_catapult_data = (
    raw_catapult_data.loc[raw_catapult_data['date'] >= '2023-06-01', cols_to_keep]  # keep only desired columns and filter by date
      .sort_values('date', ascending=False)        # sort from most recent to oldest
      .reset_index(drop=True)                      # optional: reset index
)

raw_catapult_data["date"] = pd.to_datetime(raw_catapult_data["date"], errors="coerce")
raw_catapult_data["date"] = raw_catapult_data["date"].dt.strftime("%m/%d/%Y")

# Remove rows with activity_name starting with "Activity"
if "activity_name" in raw_catapult_data.columns:
        activity_mask = raw_catapult_data["activity_name"].astype(str).str.startswith("Activity", na=False)
        removed = int(activity_mask.sum())
        if removed:
            print(f"Catapult info: Removing {removed} rows with activity_name starting with 'Activity'.")
        raw_catapult_data = raw_catapult_data.loc[~activity_mask].copy()



# --- Combine both tables (keep all columns) ---
combined = pd.concat([combined_playerteck, raw_catapult_data], ignore_index=True)

expected_cols = [
    "date",
    "athlete_name",
    "catapult_athlete_id",
    "activity_name",
    "split_name",
    "tags",
    "month_name",
    "total_duration",
    "total_player_load",
    "meterage_per_minute",
    "player_load_per_min",
]

for col in expected_cols:
    if col not in combined.columns:
        combined[col] = pd.NA

# --- Reorder columns for consistency ---
combined = combined[expected_cols]
combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
combined = combined.sort_values("date", ascending=False).reset_index(drop=True)




# JOIN CATAPULT DATA WITH OPPONENTS RANKS
# Filter only Soccer rows in your main dataframe
game_day_data = pd.read_csv("../raw_data/opponent_ranks.csv")
game_day_data['Date'] = pd.to_datetime(game_day_data['Date'])               


football_df = (
    game_day_data.loc[game_day_data['Team'] == 'Soccer', ['Date', 'Opponent']]
    .rename(columns={'Date': 'date'})
)

# Merge — keeps all rows from combined
merged_df = combined.merge(football_df, on='date', how='left')

# Assign activity labels
merged_df['activity'] = np.where(merged_df['Opponent'].notna(), 'game', 'practice')

# Sort by most recent date
merged_df = merged_df.sort_values('date', ascending=False).reset_index(drop=True)

merged_df["date"] = pd.to_datetime(merged_df["date"], errors="coerce")

# Sort descending by date (most recent → oldest)
merged_df = merged_df.sort_values("date", ascending=False).reset_index(drop=True)

# REMOVE SPLITS FROM GAMES (AKA GET RID OF 1st.half, 2nd.half)
# Normalize all three relevant columns before comparison
merged_df["activity"] = merged_df["activity"].astype(str).str.strip().str.lower()
merged_df["tags"] = merged_df["tags"].astype(str).str.strip().str.lower()
merged_df["split_name"] = merged_df["split_name"].astype(str).str.strip().str.lower()

# keep only rows where activity == "game" AND tags == "game"
merged_df["split_name"] = (
    merged_df["split_name"]
    .astype(str)        # handle NaN
    .str.strip()        # remove leading/trailing spaces
    .str.lower()        # make lowercase
)

# Remove rows where all three conditions are true
merged_df = merged_df[
    ~(
        (merged_df["activity"] == "game") &
        (merged_df["tags"] == "game") &
        (merged_df["split_name"] != "game")
    )
].reset_index(drop=True)


# ADJUST ACTIVITY TAGS FOR GAMEDAY PARCTICES IN 2024
# If activity == 'game' but tags != 'game' → set activity = 'gameday practice'
merged_df["date"] = pd.to_datetime(merged_df["date"], errors="coerce")

# Create mask for 2024 rows where activity == 'game' but tags != 'game'
mask = (
    (merged_df["date"].dt.year == 2024)
    & (merged_df["activity"].astype(str).str.strip().str.lower() == "game")
    & (merged_df["tags"].astype(str).str.strip().str.lower() != "game")
)

# Apply the replacement only to those rows
merged_df.loc[mask, "activity"] = "gameday practice"


ANCHOR = pd.Timestamp('2023-06-05')  # Monday
today = pd.Timestamp('today').normalize()

# ensure datetime
merged_df['date'] = pd.to_datetime(merged_df['date'], format='%m/%d/%Y')  # adapt if already datetime

# keep only dates on/after the first grid week (optional, but avoids negatives)
grid_week_df = merged_df.loc[merged_df['date'] >= ANCHOR].copy()

# grid week number: week 1 = 2023-06-05..2023-06-11, week 2 = next 7 days, etc.
grid_week_df['grid_week'] = ((grid_week_df['date'] - ANCHOR).dt.days // 7) + 1

# week_start and week_end for convenience
grid_week_df['week_start'] = ANCHOR + pd.to_timedelta((grid_week_df['grid_week'] - 1) * 7, unit='D')
grid_week_df['week_end']   = grid_week_df['week_start'] + pd.Timedelta(days=6)
# print(grid_week_df.head(200)) 

# ---- School start dates ----
school_starts = {
    2023: pd.Timestamp('2023-08-21'),
    2024: pd.Timestamp('2024-08-26'),
    2025: pd.Timestamp('2025-08-25'),
}

short_label = {}   # grid_week -> 'W7' or 'T-2'
uid_label   = {}   # grid_week -> '2023-W7' or '2023-T-2'
year_label  = {}   # grid_week -> 2023, 2024, 2025

for year, start in school_starts.items():
    w1_row = grid_week_df[(grid_week_df['week_start'] <= start) & (start <= grid_week_df['week_end'])]
    if w1_row.empty:
        continue
    w1 = int(w1_row.iloc[0]['grid_week'])

    # W1..W15
    for i in range(15):
        g = w1 + i
        short_label[g] = f'W{i+1}'
        uid_label[g]   = f'{year}-W{i+1}'
        year_label[g]  = year

    # T-1..T-5
    for i in range(1, 6):
        g = w1 - i
        short_label[g] = f'T-{i}'
        uid_label[g]   = f'{year}-T-{i}'
        year_label[g]  = year

# attach to grid_week_df
grid_week_df = grid_week_df.copy()
grid_week_df['week_of_school']      = grid_week_df['grid_week'].map(short_label)
grid_week_df['week_of_school_uid']  = grid_week_df['grid_week'].map(uid_label)

grid_week_df = grid_week_df.sort_values('date', ascending=False).reset_index(drop=True)

grid_week_df["date"] = pd.to_datetime(grid_week_df["date"], errors="coerce")

output_path = "../clean_data/catapult_data_for_dist.csv"
grid_week_df.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")


LOAD_THRESH = 35  # cutoff for being an active game contributor
TRAINING_ACTS = ['practice', 'gameday practice']

# 1) Row-level game status: only games count; practices are False
grid_week_df['game_status'] = (grid_week_df['activity'].eq('game')) & (grid_week_df['meterage_per_minute'] > LOAD_THRESH)

grid_week_df['weekly_status'] = (
    grid_week_df.groupby(['athlete_name', 'week_of_school_uid'])['game_status']
      .transform('any')
).fillna(False)

# print(grid_week_df.head(200)) 
# output_path = "../clean_data/catapult_data_wstatus.csv"
# grid_week_df.to_csv(output_path, index=False)
# print(f"Saved merged file to: {output_path}")

# remove practice rows with low athlete participation
practice_counts = (
    grid_week_df.loc[grid_week_df['activity'].isin(TRAINING_ACTS)]
                 .groupby('date')['catapult_athlete_id'].nunique()
                 .rename('num_athletes')
                 .reset_index()
)

# Filter out low-participation days
valid_practices = practice_counts.loc[practice_counts['num_athletes'] >= 0, 'date']
# keep only games and valid practices
df_clean = grid_week_df[
    (grid_week_df['activity'] == 'game') |
    (grid_week_df['activity'].isin(TRAINING_ACTS) & grid_week_df['date'].isin(valid_practices))
]

output_path = "../clean_data/catapult_data_practice_game_clean.csv"
df_clean.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")
print(df_clean.head(200))
