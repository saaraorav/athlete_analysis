import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

catapult_data = pd.read_csv("../clean_data/catapult_data_practice_game_clean.csv")

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

# Attach the weekly active count to each event via the unique week key 
result = (
    event_avgs.merge(active_counts, on='week_of_school_uid', how='left')
              [['date', 'activity', 'avg_player_load', 'active_player', 'week_of_school','week_of_school_uid']]
              .sort_values('date')
              .reset_index(drop=True)
)

# (optional) round for tidy display
result['avg_player_load'] = result['avg_player_load'].round(1)

print(result.head())
output_path = "../clean_data/avgload.csv"
result.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")

# --- Prep data ---
RECESS_WINDOWS = [
    {"year": 2023, "start_date": "2023-10-07", "end_date": "2023-10-20"},
    {"year": 2024, "start_date": "2024-10-01", "end_date": "2024-10-20"},
    {"year": 2025, "start_date": "2025-10-06", "end_date": "2025-10-26"},
]
result['date'] = pd.to_datetime(result['date'])
result = result.sort_values('date')

# Extract year from UID (e.g. "2024-W7" -> 2024)
result['school_year'] = result['week_of_school_uid'].str.extract(r'(\d{4})').astype(int)

# Build table for labels per week
week_labels = (
    result.groupby(['school_year', 'week_of_school_uid'], as_index=False)
          .agg({'date':'mean',
                 'week_of_school':'first',
                 'active_player':'first'})
)

# Color palette
palette = {'practice': 'red', 'game': 'blue'}

# Unique years
years = sorted(result['school_year'].unique())

# Create figure
fig, axes = plt.subplots(len(years), 1, figsize=(12, 5*len(years)), sharex=False)

if len(years) == 1:
    axes = [axes]

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
            ax.text(mid, 540, 'Recess', color='green', ha='center', va='bottom', fontsize=10)

    # Right-side y-axis
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.set_ylabel('Average Player Load', fontsize=11)
    ax.set_xlabel('Date', fontsize=11)
    ax.set_title(f'Average Player Load by Date — School Year {year}', fontsize=13, pad=10)

    # Set consistent y-axis range
    ax.set_ylim(0, 600)

    # Bottom x-axis: week labels
    ax.set_xticks(labels_year['date'])
    ax.set_xticklabels(labels_year['week_of_school'], rotation=45, ha='right')

    # Top x-axis: active player counts
    ax_top = ax.secondary_xaxis('top')
    ax_top.set_xticks(labels_year['date'])
    ax_top.set_xticklabels(labels_year['active_player'].astype(int))
    ax_top.set_xlabel('Active Players per Week', fontsize=11)

    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(title='Activity', loc='upper left')

plt.tight_layout()

# --- Export ---
output_path = "avg_player_load_by_year_connected.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.show()

print(f"✅ Plot saved to {output_path}")