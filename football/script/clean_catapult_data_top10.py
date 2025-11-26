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

output_path = "../clean_data/catapult_data_for_cont.csv"
merged_df.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")



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

# output_path = "../clean_data/catapult_data_for_dist.csv"
# grid_week_df.to_csv(output_path, index=False)
# print(f"Saved merged file to: {output_path}")


LOAD_THRESH = 100  # cutoff for being an active game contributor

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

# Create a column of tuples, then check membership
grid_week_df["year_athlete_pair"] = list(zip(grid_week_df["year"], grid_week_df[grid_name_col]))
grid_week_df["weekly_status"] = grid_week_df["year_athlete_pair"].isin(top10_pairs)
grid_week_df = grid_week_df.drop(columns=["year_athlete_pair"])  # clean up

# print(df_clean.head(200)) 

output_path = "../clean_data/catapult_data_practice_game_clean_top10.csv"
grid_week_df.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")

# For each year, check if top 10 athletes have weekly_status == True
for year in [2023, 2024, 2025]:
    # Get top 10 athletes for this year
    top10_athletes = top10_per_year[top10_per_year['year'] == year]['athlete_name'].unique()
    
    print(f"\n=== Year {year} ===")
    print(f"Top 10 athletes: {len(top10_athletes)}")
    
    for athlete in top10_athletes:
        # Check their weekly_status in grid_week_df for this year
        athlete_data = grid_week_df[(grid_week_df['year'] == year) & 
                                     (grid_week_df['athlete_name'] == athlete)]
        
        if len(athlete_data) == 0:
            print(f"  {athlete}: NOT FOUND in grid_week_df")
        else:
            has_true = (athlete_data['weekly_status'] == True).any()
            has_false = (athlete_data['weekly_status'] == False).any()
            
            if has_true and has_false:
                status = "BOTH True and False"
            elif has_true:
                status = "TRUE only"
            elif has_false:
                status = "FALSE only"
            else:
                status = "No status data"
            
            print(f"  {athlete}: {status}")


# For each year, find athletes with weekly_status == True who are NOT in top 10
for year in [2023, 2024, 2025]:
    # Get top 10 athletes for this year
    top10_athletes = set(top10_per_year[top10_per_year['year'] == year]['athlete_name'].unique())
    
    # Get athletes with weekly_status == True in grid_week_df for this year
    true_status_athletes = set(grid_week_df[(grid_week_df['year'] == year) & 
                                             (grid_week_df['weekly_status'] == True)]['athlete_name'].unique())
    
    # Find athletes with True status who are NOT in top 10
    not_in_top10 = true_status_athletes - top10_athletes
    
    print(f"\n=== Year {year} ===")
    print(f"Top 10 athletes: {len(top10_athletes)}")
    print(f"Athletes with weekly_status == True: {len(true_status_athletes)}")
    print(f"Athletes with True status NOT in top 10: {len(not_in_top10)}")
    
    if not_in_top10:
        print(f"Names: {', '.join(sorted(not_in_top10))}")