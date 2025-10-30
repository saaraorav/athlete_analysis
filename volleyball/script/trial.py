
import pandas as pd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

raw_catapult_data = pd.read_csv("../raw_data/tblCatapultVOLLEYBALLStatsByActivity.csv")

raw_catapult_data['date'] = pd.to_datetime(raw_catapult_data['date'])

data_2023 = raw_catapult_data[raw_catapult_data['date'].dt.year == 2023]
unique_athletes_2023 = (
    data_2023[['activity_name', 'date']]
    .drop_duplicates()
    .sort_values('activity_name')
    .reset_index(drop=True)
)

print(f"Unique activities in 2023: {len(unique_athletes_2023)}")
for i, row in unique_athletes_2023.iterrows():
    print(f"{row['activity_name']}, {row['date'].date()}")


# exists = (raw_catapult_data['athlete_name'] == "Taylor Johnson").any()
# print(f"Exists: {exists}")


catapult_data = pd.read_csv("../clean_data/catapult_data_for_dist.csv")

# Make sure date is datetime
catapult_data['date'] = pd.to_datetime(catapult_data['date'])

# Get the 3 most recent game dates
last_three_games = (
    catapult_data.loc[catapult_data['activity'] == 'game', 'date']
      .drop_duplicates()
      .sort_values(ascending=False)
      .tail(3)
      .tolist()
)

print("Last 3 game dates:", last_three_games)

# table with just game dates
games_df = catapult_data.loc[catapult_data['date'].isin(last_three_games)].copy()
# print(games_df.head(200))


plt.figure(figsize=(15, 6))

for date in sorted(last_three_games):
    subset = games_df.loc[games_df['date'] == date, 'total_player_load']
    plt.hist(subset, bins=20, alpha=0.5, label=date.strftime('%Y-%m-%d'))

plt.xlabel("Total Player Load")
plt.ylabel("Number of Athletes")
plt.title("Distribution of Total Player Load — Last 3 Games")
plt.legend(title="Game Date")
plt.grid(True, alpha=0.3)
x_min, x_max = plt.xlim()                 # get axis limits
plt.xticks(np.arange(0, x_max + 20, 30))
# plt.show()



import seaborn as sns
import matplotlib.dates as mdates
catapult_data = pd.read_csv("../clean_data/catapult_data_wstatus.csv")

# ensure datetime
catapult_data['date'] = pd.to_datetime(catapult_data['date'])

# pick an identifier (prefer the Catapult ID; fall back to name if needed)
id_col = 'catapult_athlete_id' if catapult_data['catapult_athlete_id'].notna().any() else 'athlete_name'


# count unique athletes for each practice date
practice_counts = (
    catapult_data.loc[catapult_data['activity'] == 'practice']
      .dropna(subset=[id_col])                           # drop rows with missing ID
      .groupby('date')[id_col].nunique()                 # unique wearers per date
      .rename('num_athletes_with_data')
      .reset_index()
      .sort_values('date', ascending=False)
)

# ensure dates are datetime and sorted
plt.figure(figsize=(10,6))
sns.barplot(data=practice_counts, x='date', y='num_athletes_with_data', color='steelblue')

plt.title('Number of Athletes Wearing Catapult per Practice')
plt.xlabel('Practice Date')
plt.ylabel('Number of Athletes')
plt.grid(True, axis='y', alpha=0.3)

# --- Set ticks every 20 entries ---
n = len(practice_counts)
tick_idx = np.arange(0, n, 20)                      # every 20th entry
tick_labels = practice_counts['date'].iloc[tick_idx].dt.strftime('%b %Y')
plt.xticks(tick_idx, tick_labels, rotation=45, ha='right')

plt.tight_layout()
# plt.show()