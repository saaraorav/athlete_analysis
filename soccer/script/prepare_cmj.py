import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


cmj_data = pd.read_csv("../clean_data/wide_cmj.csv")
catapult_data = pd.read_csv("../clean_data/catapult_data_practice_game_clean.csv")

ANCHOR = pd.Timestamp('2023-06-05')  # Monday
today = pd.Timestamp('today').normalize()

# ensure datetime
cmj_data['date'] = pd.to_datetime(cmj_data['date'], format='mixed', errors='coerce')

# keep only dates on/after the first grid week (optional, but avoids negatives)
grid_week_df = cmj_data.loc[cmj_data['date'] >= ANCHOR].copy()

# grid week number: week 1 = 2023-06-05..2023-06-11, week 2 = next 7 days, etc.
grid_week_df['grid_week'] = ((grid_week_df['date'] - ANCHOR).dt.days // 7) + 1

# week_start and week_end for convenience
grid_week_df['week_start'] = ANCHOR + pd.to_timedelta((grid_week_df['grid_week'] - 1) * 7, unit='D')
grid_week_df['week_end']   = grid_week_df['week_start'] + pd.Timedelta(days=6)

# ---- School start dates ----
school_starts = {
    # 2023: pd.Timestamp('2023-08-21'),
    2024: pd.Timestamp('2024-08-26'),
    2025: pd.Timestamp('2025-08-25'),
}

short_label = {}
uid_label   = {}

years = sorted(school_starts.keys())
max_gw = int(grid_week_df['grid_week'].max())

for i, year in enumerate(years):
    start = school_starts[year]
    w1 = ((start.normalize() - ANCHOR).days // 7) + 1  # grid week containing school start

    if i + 1 < len(years):
        next_start = school_starts[years[i + 1]]
        w_end_excl = ((next_start.normalize() - ANCHOR).days // 7) + 1  # up to next start
    else:
        w_end_excl = max_gw + 1

    # Label W1..Wk all the way until the next year's start (exclusive)
    k = 1
    for g in range(w1, min(w_end_excl, max_gw + 1)):
        short_label[g] = f'W{k}'
        uid_label[g]   = f'{year}-W{k}'
        k += 1

    # Optional: pre-term labels T-1..T-5
    for t in range(1, 6):
        g = w1 - t
        if g >= 1:
            short_label[g] = f'T-{t}'
            uid_label[g]   = f'{year}-T-{t}'

# attach to df
grid_week_df['week_of_school']     = grid_week_df['grid_week'].map(short_label)
grid_week_df['week_of_school_uid'] = grid_week_df['grid_week'].map(uid_label)
grid_week_df = grid_week_df.sort_values('date', ascending=False).reset_index(drop=True)

print(grid_week_df.head(200))


status = catapult_data[['athlete_name', 'week_of_school_uid', 'weekly_status']].copy()
status['weekly_status'] = (
    status['weekly_status']
    .astype(str).str.strip().str.lower()
    .map({'true': True, 'false': False, '1': True, '0': False})
    .astype('boolean')
)

# 2) Check for conflicts (shouldn’t exist if data are clean)
nuniq = (
    status.groupby(['athlete_name', 'week_of_school_uid'])['weekly_status']
          .nunique()
          .reset_index(name='nunique')
)
conflicts = nuniq[nuniq['nunique'] > 1]
if not conflicts.empty:
    print("!!!!!! Conflicting weekly_status values detected; using True if any True present for those keys.")

# 3) Collapse to one row per (athlete, week). Since values should match, 'max' is fine.
status_by_week = (
    status.groupby(['athlete_name', 'week_of_school_uid'], as_index=False)
          .agg(weekly_status=('weekly_status', 'max'))
)

# 4) Clean merge (m:1) from grid_week_df onto status
merged = grid_week_df.merge(
    status_by_week,
    left_on=['name', 'week_of_school_uid'],
    right_on=['athlete_name', 'week_of_school_uid'],
    how='left',
    validate='m:1'      # ensures right side is unique per key
).drop(columns=['athlete_name'])

# count how many times weekly_status == True per unique date
# remove jump-dates with fewer than 25 active athletes
active_counts = (
    merged[merged['weekly_status'] == True]
      .groupby('date')['weekly_status']
      .count()
      .reset_index(name='active_count')
)

# find which dates have at least 25 True values
valid_dates = active_counts.loc[active_counts['active_count'] >= 5, 'date']

# keep only those dates in your dataframe
filtered_df = merged[merged['date'].isin(valid_dates)].copy()

output_path = "../clean_data/cmj_wstatus.csv"
filtered_df.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")

