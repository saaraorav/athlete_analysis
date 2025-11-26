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

# print(grid_week_df.head(200))

output_path = "../clean_data/cmj_grid_week.csv"
grid_week_df.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")



top_cont = pd.read_csv("../clean_data/top_contributors.csv")
top_cont['athlete_name'] = top_cont['athlete_name'].str.strip()

# First, extract year from grid_week_df's date column
grid_week_df['year'] = pd.to_datetime(grid_week_df['date']).dt.year
grid_week_df['name'] = grid_week_df['name'].str.strip()

# Merge with top_cont - specify left_on and right_on since column names differ
grid_week_df = grid_week_df.merge(
    top_cont[['year', 'athlete_name', 'avg_minutes_played']], 
    left_on=['year', 'name'],
    right_on=['year', 'athlete_name'], 
    how='left'
)

# Drop the duplicate athlete_name column since you already have 'name'
grid_week_df = grid_week_df.drop(columns=['athlete_name'])

# Create weekly_status column
grid_week_df['weekly_status'] = grid_week_df['avg_minutes_played'] >= 45

output_path = "../clean_data/cmj_wstatus.csv"
grid_week_df.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")


# # Group by year and weekly_status to count athletes
# status_summary = (
#     grid_week_df.groupby(['year', 'weekly_status'])['name']
#     .nunique()
#     .reset_index()
#     .rename(columns={'name': 'athlete_count'})
# )

# print(status_summary)

# # Or if you want to see the actual athlete names:
# print("\n=== Athletes by Year and Weekly Status ===\n")

# for year in [2024, 2025]:
#     print(f"\nYear {year}:")
    
#     true_athletes = grid_week_df[(grid_week_df['year'] == year) & 
#                                   (grid_week_df['weekly_status'] == True)]['name'].unique()
#     print(f"  Weekly Status TRUE ({len(true_athletes)} athletes):")
#     print(f"    {', '.join(sorted(true_athletes))}")
    
#     false_athletes = grid_week_df[(grid_week_df['year'] == year) & 
#                                    (grid_week_df['weekly_status'] == False)]['name'].unique()
#     print(f"  Weekly Status FALSE ({len(false_athletes)} athletes):")
#     print(f"    {', '.join(sorted(false_athletes))}")


# # For each year, find athletes who have BOTH True and False weekly_status
# for year in [2024, 2025]:
#     year_data = grid_week_df[grid_week_df['year'] == year]
    
#     # Get athletes with True status
#     true_athletes = set(year_data[year_data['weekly_status'] == True]['name'].unique())
    
#     # Get athletes with False status
#     false_athletes = set(year_data[year_data['weekly_status'] == False]['name'].unique())
    
#     # Find intersection (athletes with BOTH statuses)
#     both_status = true_athletes & false_athletes
    
#     print(f"\nYear {year}:")
#     print(f"  Athletes with BOTH True and False weekly_status: {len(both_status)}")
#     print(f"  Names: {', '.join(sorted(both_status))}")


for year in [2024, 2025]:
    # Get athletes from top_cont with avg_minutes_played >= 45 for this year
    top_athletes = set(top_cont[(top_cont['year'] == year) & 
                                    (top_cont['avg_minutes_played'] >= 45)]['athlete_name'].unique())

    # Get athletes from grid_week_df with weekly_status == True for this year
    grid_true_athletes = set(grid_week_df[(grid_week_df['year'] == year) & 
                                            (grid_week_df['weekly_status'] == True)]['name'].unique())

    # Find athletes in top_cont but NOT in grid_week_df with True status
    missing_athletes = top_athletes - grid_true_athletes

    print(f"\nYear {year}:")
    print(f"  Athletes with avg_minutes >= 45 in top_cont but NOT in weekly_status True: {len(missing_athletes)}")
    print(f"  Names: {', '.join(sorted(missing_athletes))}")