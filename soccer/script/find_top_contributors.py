import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("../clean_data/minutesplayed_clean.csv")
# Extract year from date column
df['year'] = pd.to_datetime(df['date']).dt.year

# Filter for 2024 and 2025
df_filtered = df[df['year'].isin([2024, 2025])]

# Clean athlete names
df_filtered['athlete_name'] = df_filtered['athlete_name'].str.strip()

yearly_load = (
    df.assign(
        year=lambda x: pd.to_datetime(x['date']).dt.year,
        athlete_name=lambda x: x['athlete_name'].str.strip()
    )
    .query('year in [2024, 2025]')
    .groupby(["year", "athlete_name"], as_index=False)
    .agg(avg_minutes_played=("minutes_played", "mean"))
    .sort_values(["year", "avg_minutes_played"], ascending=False)
    .assign(
        avg_minutes_played=lambda x: x['avg_minutes_played'].round().astype(int))
)


output_path = "../clean_data/top_contributors.csv"
yearly_load.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")