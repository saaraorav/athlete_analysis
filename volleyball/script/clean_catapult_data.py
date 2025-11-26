# from matplotlib.pylab import NaN
import pandas as pd
import numpy as np

# Example: your DataFrame
# need to be inside volleyball/script folder to run correctly
raw_catapult_data = pd.read_csv("../raw_data/tblCatapultVOLLEYBALLStatsByActivity.csv")

game_day_data = pd.read_csv("../raw_data/team_schedule.csv")

# List of columns to keep
cols_to_keep = ['date', 'athlete_name', 'catapult_athlete_id', 'activity_name', 'position_name','month_name', 'total_duration', 'total_player_load']
raw_catapult_data['date'] = pd.to_datetime(raw_catapult_data['date'], format='%m/%d/%Y')

# Rename Gaby Mansfield to Gabriela Mansfield in athlete_name column
raw_catapult_data['athlete_name'] = raw_catapult_data['athlete_name'].replace('Gaby Mansfield', 'Gabriela Mansfield')

raw_catapult_data['year'] = pd.to_datetime(raw_catapult_data['date']).dt.year
# print unique athletes in df_clean
# for year in sorted(raw_catapult_data['year'].unique()):
#     athletes = raw_catapult_data[raw_catapult_data['year'] == year]['athlete_name'].unique()
#     print(f"\n=== Year {year} ===")
#     print(f"Total unique athletes: {len(athletes)}")
#     for athlete in sorted(athletes):
#         print(f"  {athlete}")

athletes_to_check = ['Cindy Tchouangwa']
filtered_df = raw_catapult_data[raw_catapult_data['athlete_name'].isin(athletes_to_check)]
filtered_df.to_csv('../clean_data/specific_athletes.csv', index=False)

# Filter columns, date, and sort
raw_catapult_data = (
    raw_catapult_data.loc[raw_catapult_data['date'] >= '2024-06-01', cols_to_keep]  # keep only desired columns and filter by date
      .sort_values('date', ascending=False)        # sort from most recent to oldest
      .reset_index(drop=True)                      # optional: reset index
)

# # print all unique athlete names, filter for date just 2024
# unique_athletes_2024 = raw_catapult_data[raw_catapult_data['date'].dt.year == 2024]['athlete_name'].unique()
# print("Unique athlete names in 2024:")
# for athlete in unique_athletes_2024:
#     print(athlete)

# join catapult data with opponents rank
# game_day_data['Date'] = pd.to_datetime(game_day_data['Date'], format='%m/%d/%Y')
game_day_data['Date'] = pd.to_datetime(game_day_data['Date'])               

# Filter only Football rows in your main dataframe
football_df = game_day_data.loc[game_day_data['Team'] == 'Volleyball', ['Date', 'Opponent', 'sets']].rename(columns={'Date': 'date'})

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

# Define what counts as a valid game name
valid_prefixes = ('Game', 'Exhibition', 'Conference')

# Make sure we’re only looking at rows currently labeled as "game"
mask_game = merged_df['activity'] == 'game'

# Find "game" rows whose activity_name does NOT start with those prefixes
mask_invalid_game = (
    mask_game &
    ~merged_df['activity_name'].fillna('').str.startswith(valid_prefixes)
)

# Update those rows to 'practice' while keeping everything else unchanged
merged_df.loc[mask_invalid_game, 'activity'] = 'gameday practice'

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

LOAD_THRESH = 0 # cutoff for being an active game contributor
TRAINING_ACTS = ['practice', 'gameday practice']

# 1) Row-level game status: only games count; practices are False
grid_week_df['game_status'] = (grid_week_df['activity'].eq('game')) & (grid_week_df['total_player_load'] > LOAD_THRESH)

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
valid_practices = practice_counts.loc[practice_counts['num_athletes'] >= 7, 'date']
# keep only games and valid practices
df_clean = grid_week_df[
    (grid_week_df['activity'] == 'game') |
    (grid_week_df['activity'].isin(TRAINING_ACTS) & grid_week_df['date'].isin(valid_practices))
]

output_path = "../clean_data/catapult_data_practice_game_clean_entire_team.csv"
df_clean.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")
# print(df_clean.head(200))


df_clean['year'] = pd.to_datetime(df_clean['date']).dt.year

for year in sorted(df_clean['year'].unique()):
    athletes = df_clean[df_clean['year'] == year]['athlete_name'].unique()
    print(f"\n=== Year {year} ===")
    print(f"Total unique athletes: {len(athletes)}")
    for athlete in sorted(athletes):
        print(f"  {athlete}")


# Get all unique athletes with weekly_status == True
true_status_athletes = grid_week_df[grid_week_df['weekly_status'] == True]['athlete_name'].unique()

# print(f"Total unique athletes with weekly_status == True: {len(true_status_athletes)}")
# print("\nAthletes:")
# for athlete in sorted(true_status_athletes):
#     print(f"  {athlete}")


# All Cindy's games
all_cindy_games = grid_week_df[
    (grid_week_df['athlete_name'] == 'Cindy Tchouangwa') & 
    (grid_week_df['activity'] == 'game')
]

print(f"Total games: {len(all_cindy_games)}")
print(f"Games with weekly_status == True: {(all_cindy_games['weekly_status'] == True).sum()}")
print(f"Games with weekly_status == False: {(all_cindy_games['weekly_status'] == False).sum()}")

print("\nAll games by week:")
print(all_cindy_games[['date', 'week_of_school', 'total_player_load', 'game_status', 'weekly_status']].sort_values('date'))