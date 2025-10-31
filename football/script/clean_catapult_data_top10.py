import pandas as pd
import numpy as np

# Example: your DataFrame
raw_catapult_data = pd.read_csv("../raw_data/tblCatapultFOOTBALLStatsByActivity.csv")
top10_per_year = pd.read_csv("../clean_data/top_contributors.csv")


# List of columns to keep
cols_to_keep = ['date', 'athlete_name', 'catapult_athlete_id', 'activity_name', 'position_name','month_name', 'total_duration', 'total_player_load', 'meterage_per_minute']
raw_catapult_data['date'] = pd.to_datetime(raw_catapult_data['date'], format='%m/%d/%Y')

# Filter columns, date, and sort
raw_catapult_data = (
    raw_catapult_data.loc[raw_catapult_data['date'] >= '2023-06-01', cols_to_keep]  # keep only desired columns and filter by date
      .sort_values('date', ascending=False)        # sort from most recent to oldest
      .reset_index(drop=True)                      # optional: reset index
)

# print(raw_catapult_data.head()) 

# join catapult data with opponents rank
game_day_data = pd.read_csv("../raw_data/team_schedule.csv")
game_day_data['Date'] = pd.to_datetime(game_day_data['Date'])               

# Filter only Football rows in your main dataframe
football_df = game_day_data.loc[game_day_data['Team'] == 'Football', ['Date', 'Opponent']].rename(columns={'Date': 'date'})

# Join on date — inner keeps only matching game days
merged_df = pd.merge(
    raw_catapult_data,
    football_df,
    on='date',
    how='left' # keeps all rows from raw_catapult_data
)

# Sort newest → oldest if you’d like
merged_df = merged_df.sort_values('date', ascending=False).reset_index(drop=True)

merged_df['activity'] = np.where(merged_df['Opponent'].isna(), 'practice', 'game')
merged_df = merged_df.loc[
    (merged_df['total_player_load'] != 0) & 
    (merged_df['total_duration'] != 0)
].reset_index(drop=True)

# remove duplicates: keep first occurrence (newest date) per athlete/activity/date
merged_df = merged_df.drop_duplicates(subset=['date', 'athlete_name', 'activity_name'], keep='first')


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

# print(grid_week_df.head(200)) 

output_path = "../clean_data/catapult_data_for_dist.csv"
grid_week_df.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")


LOAD_THRESH = 100  # cutoff for being an active game contributor

# 1) Row-level game status: only games count; practices are False
# grid_week_df['game_status'] = (grid_week_df['activity'].eq('game')) & (grid_week_df['total_player_load'] > LOAD_THRESH)

# grid_week_df['weekly_status'] = (
#     grid_week_df.groupby(['athlete_name', 'week_of_school_uid'])['game_status']
#       .transform('any')
# ).fillna(False)

# # print(grid_week_df.head(200)) 
# output_path = "../clean_data/catapult_data_wstatus.csv"
# grid_week_df.to_csv(output_path, index=False)
# print(f"Saved merged file to: {output_path}")


# # remove practice rows with low athlete participation
# practice_counts = (
#     grid_week_df.loc[grid_week_df['activity'] == 'practice']
#       .groupby('date')['catapult_athlete_id'].nunique()
#       .rename('num_athletes')
#       .reset_index()
# )

# # Filter out low-participation days
# valid_practices = practice_counts.loc[practice_counts['num_athletes'] >= 35, 'date']
# # keep only games and valid practices
# df_clean = grid_week_df[
#     (grid_week_df['activity'] == 'game') |
#     ((grid_week_df['activity'] == 'practice') & (grid_week_df['date'].isin(valid_practices)))
# ]

grid_week_df = grid_week_df.copy()
grid_week_df["date"] = pd.to_datetime(grid_week_df["date"], errors="coerce")
grid_week_df["year"] = grid_week_df["date"].dt.year

# Identify athlete/name columns
grid_name_col = "athlete_name" if "athlete_name" in grid_week_df.columns else "name"
top_name_col  = "athlete_name" if "athlete_name" in top10_per_year.columns else "name"

# --- Build set of (year, athlete) for top-10 cohort ---
top10_pairs = (
    top10_per_year[["year", top_name_col]]
    .dropna()
    .drop_duplicates()
    .apply(tuple, axis=1)
)
top10_pairs = set(top10_pairs.tolist())

grid_week_df["weekly_status"] = pd.Series(
    list(zip(grid_week_df["year"], grid_week_df[grid_name_col]))
).isin(top10_pairs)

# print(df_clean.head(200)) 

output_path = "../clean_data/catapult_data_practice_game_clean_top10.csv"
grid_week_df.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")