import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D
# import numpy as np

catapult_data = pd.read_csv("../clean_data/catapult_data_practice_game_clean_top10.csv")
cmj_data = pd.read_csv("../clean_data/cmj_wstatus_top10.csv")

weeks_cmj = cmj_data.loc[cmj_data['week_of_school_uid'].notna()].copy()

# Ensure datetime
catapult_data['date'] = pd.to_datetime(catapult_data['date'])

# Keep only rows that belong to a labeled school week
df_weeks = catapult_data.loc[catapult_data['week_of_school_uid'].notna()].copy()

# Count active players per week (weekly_status == True)
active_counts = (
    df_weeks.loc[df_weeks['weekly_status']]
      .groupby('week_of_school_uid')['athlete_name']
      .nunique()
      .rename('active_player')
      .reset_index()
)

# Per-event (date-level) average using ONLY athletes with weekly_status == True
#     Keep games and practices separate; no weekly pooling.
event_avgs = (
    df_weeks.loc[df_weeks['weekly_status']]
      .groupby(['date', 'activity', 'week_of_school_uid'], as_index=False)
      .agg(
          avg_player_load=('total_player_load', 'mean'),
          num_athletes=('athlete_name', 'nunique'),
          week_of_school=('week_of_school', 'first')  # for display
      )
)

week_starts = (
    df_weeks.groupby('week_of_school_uid', as_index=False)
             .agg(week_start=('week_start', 'first'))
)

result = (
    event_avgs
      .merge(active_counts, on='week_of_school_uid', how='left')
      .merge(week_starts, on='week_of_school_uid', how='left')
      [['date', 'activity', 'avg_player_load', 'num_athletes','active_player',
        'week_of_school', 'week_of_school_uid', 'week_start']]
      .sort_values('date')
      .reset_index(drop=True)
)

# (optional) round for tidy display
result['avg_player_load'] = result['avg_player_load'].round(1)

# print(result.head())
output_path = "../clean_data/avgload_top10.csv"
result.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")

# COMPUTE AVG PEAK POEWER BM PER WEEK for active athletes

# Per-event (date-level) average using ONLY athletes with weekly_status == True
# Keep games and practices separate; no weekly pooling.
cmj_event_avgs = (
    weeks_cmj.loc[weeks_cmj['weekly_status'] & weeks_cmj['peak_power_bm'].notna()]
      .groupby(['date', 'week_of_school_uid'], as_index=False)
      .agg(
          avg_peak_power_bm=('peak_power_bm', 'mean'),
          num_athletes=('name', 'nunique'),
          week_of_school=('week_of_school', 'first')  # for display
      )
)

week_starts = (
    weeks_cmj.groupby('week_of_school_uid', as_index=False)
            .agg(week_start=('week_start', 'first'))
)

cmj_result = (
    cmj_event_avgs
      .merge(active_counts, on='week_of_school_uid', how='left')
      .merge(week_starts, on='week_of_school_uid', how='left')
      [['date', 'avg_peak_power_bm', 'num_athletes','active_player',
        'week_of_school', 'week_of_school_uid', 'week_start']]
      .sort_values('date')
      .reset_index(drop=True)
)

# print(result.head())
output_path = "../clean_data/avgpeakpower_top10.csv"
cmj_result.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")

# --- Prep data ---
MIDTERM_WINDOWS = [
    {"year": 2023, "start_date": "2023-10-02", "end_date": "2023-10-23"},
    {"year": 2024, "start_date": "2024-10-07", "end_date": "2024-10-28"},
    {"year": 2025, "start_date": "2025-10-06", "end_date": "2025-10-27"},
]

RECESS_WINDOWS = [
    {"year": 2023, "start_date": "2023-10-09", "end_date": "2023-10-10"},
    {"year": 2024, "start_date": "2024-10-14", "end_date": "2024-10-15"},
    {"year": 2025, "start_date": "2025-10-13", "end_date": "2025-10-14"},
]

result['date'] = pd.to_datetime(result['date'])
result['week_start'] = pd.to_datetime(result['week_start'])
result = result.sort_values('date')

# Extract year from UID (e.g. "2024-W7" -> 2024)
result['school_year'] = result['week_of_school_uid'].str.extract(r'(\d{4})').astype(int)

df_weeks['week_start'] = pd.to_datetime(df_weeks['week_start'], errors='coerce')

# 2) If school_year is somehow missing, derive it from UID (fallback)
if 'school_year' not in df_weeks.columns:
    df_weeks['school_year'] = df_weeks['week_of_school_uid'].str.extract(r'(\d{4})').astype(int)

# 3) Build the full calendar of academic weeks from df_weeks itself
all_weeks = (
    df_weeks[['school_year', 'week_of_school_uid', 'week_start', 'week_of_school']]
    .drop_duplicates()
    .sort_values(['school_year', 'week_start'])
)

# 4) Pull per-week active counts from result (de-dup in case of multiple rows per week)
active_per_week = (
    result[['week_of_school_uid', 'active_player']]
    .drop_duplicates(subset=['week_of_school_uid'])
)

# 5) Merge to include weeks with no data; fill missing active_player with 0
week_labels = (
    all_weeks.merge(active_per_week, on='week_of_school_uid', how='left')
             .fillna({'active_player': 0})
)

# (Optional) make active_player integer
week_labels['active_player'] = week_labels['active_player'].astype(int)

# 6) Add missing weeks W1-W15 for each school_year
all_needed_weeks = [f'W{i}' for i in range(1, 16)]  # W1, W2, ..., W15
missing_rows = []

for year in week_labels['school_year'].unique():
    year_data = week_labels[week_labels['school_year'] == year]
    existing_weeks = set(year_data['week_of_school'].values)
    missing_weeks = [w for w in all_needed_weeks if w not in existing_weeks]

    if missing_weeks:
        # Get the latest week_start to calculate missing weeks
        latest_week_start = year_data['week_start'].max()
        # Get the latest week number from existing data
        year_data['week_num'] = year_data['week_of_school'].str.extract(r'W(\d+)').astype('Int64')
        latest_week_num = year_data['week_num'].max()

        for missing_week in missing_weeks:
            missing_week_num = int(missing_week.replace('W', ''))
            # Calculate week_start: latest + 7 days per week difference
            week_diff = missing_week_num - latest_week_num
            calculated_week_start = latest_week_start + pd.Timedelta(days=7*week_diff)

            missing_rows.append({
                'school_year': year,
                'week_of_school_uid': f'{year}-{missing_week}',
                'week_start': calculated_week_start,
                'week_of_school': missing_week,
                'active_player': 0
            })

if missing_rows:
    missing_df = pd.DataFrame(missing_rows)
    week_labels = pd.concat([week_labels, missing_df], ignore_index=True)
    week_labels = week_labels.sort_values(['school_year', 'week_start']).reset_index(drop=True)

result = result[result['week_of_school'].str.match(r'^W\d+', na=False)]
week_labels = week_labels[week_labels['week_of_school'].str.match(r'^W\d+', na=False)]

# Color palette
palette = {'practice': 'red', 'game': 'blue'}

# Unique years
years = sorted(result['school_year'].unique())

# Create figure
fig, axes = plt.subplots(len(years), 1, figsize=(12, 5*len(years)), sharex=False)

if len(years) == 1:
    axes = [axes]

# --- Ensure cmj_result has real datetimes ---
cmj_result['date'] = pd.to_datetime(cmj_result['date'], errors='coerce')
cmj_result = cmj_result.dropna(subset=['date'])  # drop rows that failed to parse
cmj_result = cmj_result[cmj_result['week_of_school'].astype(str).str.match(r'^W\d+', na=False)]

# (Optional sanity check)
print("cmj_result['date'] dtype:", cmj_result['date'].dtype)


m = result['avg_player_load'].dropna()
meter_lo = max(0, m.min() - 0.05*(m.max()-m.min()))
meter_hi = m.max() + 0.05*(m.max()-m.min())

pp = cmj_result['avg_peak_power_bm'].dropna()
pp_lo = pp.min()*0.95
pp_hi = pp.max()*1.05

output_path = "../clean_data/week_labels.csv"
week_labels.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")

# --- Plot for each year ---
for ax, year in zip(axes, years):
    ax.set_title(f'{year}', fontsize=12, pad=10)
    data_year = result[result['school_year'] == year]
    labels_year = week_labels[week_labels['school_year'] == year]
    print(labels_year)

    # Plot lines (connect dots)
    sns.lineplot(
        data=data_year,
        x='date', y='avg_player_load',
        hue='activity', palette=palette,
        alpha=0.5, linewidth=1.5, ax=ax, legend=False
    )

    # Scatter on top (for visible dots)
    sns.scatterplot(
        data=data_year,
        x='date', y='avg_player_load',
        hue='activity', palette=palette,
        s=70, ax=ax, legend=True
    )
    for window in MIDTERM_WINDOWS:
        if window['year'] == year:
            start = pd.to_datetime(window['start_date'])
            end = pd.to_datetime(window['end_date'])
            ax.axvspan(start, end, color='green', alpha=0.15)
            # optional label
            mid = start + (end - start) / 2
            ax.text(mid, 650, 'Midterms', color='green', ha='center', va='bottom', fontsize=10)

    for window in RECESS_WINDOWS:
        if window['year'] == year:
            start = pd.to_datetime(window['start_date'])
            end = pd.to_datetime(window['end_date'])
            ax.axvspan(start, end, color='red', alpha=0.15)
            # optional label
            mid = start + (end - start) / 2
            ax.text(mid, 600, 'Recess', color='red', ha='center', va='bottom', fontsize=10)

    # Set consistent y-axis range
    # ax.set_ylim(50, 700)

    # Bottom x-axis: week labels
    ax.set_xticks(labels_year['week_start'])
    ax.set_xticklabels(labels_year['week_of_school'], rotation=45, ha='right')

    ax.grid(True, linestyle='--', alpha=0.4)
    # Set x-axis limits with buffer for better visualization
    buffer = pd.Timedelta(days=2)
    buffer2 = pd.Timedelta(days=7)
    ax.set_xlim(labels_year['week_start'].min() - buffer, labels_year['week_start'].max() + buffer2)

    # --- LEFT axis = Peak Power / BM (ax_left) ---
    ax_left = ax.twinx()
    ax_left.yaxis.set_label_position("left")
    ax_left.yaxis.tick_left()
    ax_left.spines['left'].set_visible(True)
    # ax_left.spines['left'].set_position(('axes',))  # shove the PP/BM axis to the left edge
    ax_left.spines['right'].set_visible(False)
    ax_left.tick_params(axis='y', which='both', left=True,  labelleft=True,
                        right=False, labelright=False)
    ax_left.set_ylabel('Peak Power / BM', fontsize=11, color='black')

    # --- RIGHT axis = Player Load (ax) ---
    ax.yaxis.set_label_position("right")
    ax.yaxis.tick_right()
    ax.spines['right'].set_visible(True)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', which='both', right=True, labelright=True,
                left=False,  labelleft=False)
    ax.set_ylabel('Average Player Load', fontsize=11, color='black')

    ax.set_xlabel('Week of School', fontsize=11)

    cmj_year = cmj_result[cmj_result['date'].dt.year == year]

    # plot Peak Power / BM as a black line + dots
    sns.lineplot(
        data=cmj_year,
        x='date', y='avg_peak_power_bm',
        color='black', linewidth=2, ax=ax_left, label='Peak Power / BM'
    )
    sns.scatterplot(
        data=cmj_year,
        x='date', y='avg_peak_power_bm',
        color='black', s=40, ax=ax_left
    )
    leg_left = ax.get_legend()
    if leg_left is not None:
        leg_left.remove()
        
    leg_right = ax_left.get_legend()
    if leg_right is not None:
        leg_right.remove()

    # RIGHT axis = meterage scale identical across subplots
    ax.set_ylim(meter_lo, meter_hi)

    # LEFT axis = PP/BM scale identical across subplots
    ax_left.set_ylim(pp_lo, pp_hi)

# --- Legend handling ---
# Collect all handles and labels from both axes
handles1, labels1 = ax.get_legend_handles_labels()
handles2, labels2 = ax_left.get_legend_handles_labels()

# Customize labels as needed
labels1 = [f"{label} meterage per minute" for label in labels1]

all_handles = handles1 + handles2
all_labels = labels1 + labels2

# Create custom legend handles for all three activities
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=palette['practice'], 
           markersize=8, label='practice load'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=palette['game'], 
           markersize=8, label='game load'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='black', markersize=8, label='Peak Power / BM')
]
fig.suptitle('Football Player Loads for Top Contributors', fontsize=16, y=0.99)

# Create a single figure-level legend
fig.legend(
    handles=legend_elements,
    loc='upper center',
    bbox_to_anchor=(0.15, 1.003),  # Top left corner
    ncol=1,  # Adjust based on number of items
    frameon=True
)

plt.tight_layout()

# --- Export ---
output_path = "avg_player_load_by_year_top10.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
# plt.show()

print(f"✅ Plot saved to {output_path}")









# -------- BARPLOT OF ATHLETE PARTICIPATION BY ACTIVITY TYPE --------
# fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=False)
fig, axes = plt.subplots(len(years), 1, figsize=(12, 5*len(years)), sharex=False)
years = [2023,2024, 2025]

# Width of each bar (in days)
bar_width = pd.Timedelta(days=0.8)  # Slightly less than 1 day for visual separation

for ax, year in zip(axes, years):
    data_year = result[result['school_year'] == year].copy()
    labels_year = week_labels[week_labels['school_year'] == year]
    
    # Get unique activities for this year
    activities = data_year['activity'].unique()
    n_activities = len(activities)

    offsets = {
        'practice': -1.5 * bar_width,
        'game': -0.5 * bar_width,
        'cmj': 0.5 * bar_width  # NOW IT'S DEFINED HERE
    }
    
    # Plot bars for each activity
    for activity in activities:
        activity_data = data_year[data_year['activity'] == activity]
        
        # Adjust x-position based on activity
        x_positions = activity_data['date'] + offsets.get(activity, pd.Timedelta(days=0))
        
        ax.bar(
            x_positions,
            activity_data['num_athletes'],
            width=bar_width,
            color=palette[activity],
            label=f'{activity}',
            alpha=0.8
        )

    cmj_year = cmj_result[cmj_result['date'].dt.year == year]
    # Add Peak Power / BM (CMJ) bars
    if len(cmj_year) > 0:
        x_positions_cmj = cmj_year['date'] + offsets['cmj']
        
        ax.bar(
            x_positions_cmj,
            cmj_year['num_athletes'],
            width=bar_width,
            color='black',
            label='Peak Power / BM',
            alpha=0.8
        )
    
    # Match x-axis formatting from activity figure
    ax.set_xticks(labels_year['week_start'])
    ax.set_xticklabels(labels_year['week_of_school'], rotation=45, ha='right')
    
    ax.grid(True, linestyle='--', alpha=0.4, axis='y')
    ax.set_ylabel('Number of Athletes', fontsize=11)
    ax.set_xlabel('Week of School', fontsize=11)
    
    # Match x-axis limits
    buffer = pd.Timedelta(days=7)
    ax.set_xlim(labels_year['week_start'].min() - buffer, 
                labels_year['week_start'].max() + buffer)

# Create legend
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='s', color='w', markerfacecolor=palette['practice'], 
           markersize=10, label='practice'),
    Line2D([0], [0], marker='s', color='w', markerfacecolor=palette['game'], 
           markersize=10, label='game'),
    Line2D([0], [0], marker='s', color='w', markerfacecolor='black', 
           markersize=10, label='Peak Power / BM')  # Added CMJ
]

fig.legend(
    handles=legend_elements,
    loc='upper center',
    bbox_to_anchor=(0.5, 0.98),
    ncol=4,
    frameon=True
)

fig.tight_layout(rect=[0, 0, 1, 0.96])

output_path = "athlete_participation_by_activity.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"✅ Plot saved to {output_path}")