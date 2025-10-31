import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
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
      [['date', 'activity', 'avg_player_load', 'active_player',
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
      [['date', 'avg_peak_power_bm', 'active_player',
        'week_of_school', 'week_of_school_uid', 'week_start']]
      .sort_values('date')
      .reset_index(drop=True)
)

# print(result.head())
output_path = "../clean_data/avgpeakpower_top10.csv"
cmj_result.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")

# --- Prep data ---
RECESS_WINDOWS = [
    {"year": 2023, "start_date": "2023-10-02", "end_date": "2023-10-23"},
    {"year": 2024, "start_date": "2024-10-07", "end_date": "2024-10-28"},
    {"year": 2025, "start_date": "2025-10-06", "end_date": "2025-10-27"},
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

# --- Plot for each year ---
for ax, year in zip(axes, years):
    data_year = result[result['school_year'] == year]
    labels_year = week_labels[week_labels['school_year'] == year]

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
    for window in RECESS_WINDOWS:
        if window['year'] == year:
            start = pd.to_datetime(window['start_date'])
            end = pd.to_datetime(window['end_date'])
            ax.axvspan(start, end, color='green', alpha=0.15)
            # optional label
            mid = start + (end - start) / 2
            ax.text(mid, 650, 'Recess', color='green', ha='center', va='bottom', fontsize=10)

    # Set consistent y-axis range
    # ax.set_ylim(50, 700)

    # Bottom x-axis: week labels
    ax.set_xticks(labels_year['week_start'])
    ax.set_xticklabels(labels_year['week_of_school'], rotation=45, ha='right')

    # Top x-axis: active player counts
    ax_top = ax.secondary_xaxis('top')
    ax_top.set_xticks(labels_year['week_start'])
    ax_top.set_xticklabels(labels_year['active_player'].astype(int))
    ax_top.set_xlabel(f'Active Players per Week - {year}', fontsize=11)

    ax.grid(True, linestyle='--', alpha=0.4)

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
    # ax_left.set_ylim(52, 70)

    # RIGHT axis = meterage scale identical across subplots
    ax.set_ylim(meter_lo, meter_hi)

    # LEFT axis = PP/BM scale identical across subplots
    ax_left.set_ylim(pp_lo, pp_hi)

    # --- Legend handling ---
    # Remove the right legend (from Peak Power / BM axis)
    leg_right = ax_left.get_legend()
    if leg_right is not None:
        leg_right.remove()

    # Keep the left legend (practice/game) in upper left
    leg_left = ax.get_legend()
    if leg_left is not None:
        leg_left.set_title("Activity")
        leg_left.set_bbox_to_anchor((0.02, 0.95))  # optional: nudge it slightly

    # optional combined legend
    handles1, labels1 = ax.get_legend_handles_labels()
    handles2, labels2 = ax_left.get_legend_handles_labels()
    labels1 = [f"{label} load" for label in labels1]
    ax.legend(handles1 + handles2, labels1 + labels2, loc='upper left')

plt.tight_layout()

# --- Export ---
output_path = "avg_player_load_by_year_top10.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
# plt.show()

print(f"✅ Plot saved to {output_path}")