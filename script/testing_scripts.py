import pandas as pd

# df = pd.read_csv("script/outputs/wsoc_catapult_subset.csv")
# df2 = pd.read_csv("script/outputs/playerteck_combined_clean.csv")
# df3 = pd.read_csv("raw_data/MASTER_all_CMJmetrics.csv")
# df4 = pd.read_csv("script/outputs/wsoc_playertek_combined_aligned.csv") 

# # Print all column names
# print(df3.columns.tolist())
# print(df["athlete_name"].unique())

# print(df3.loc[df3["typeName"] == "Women's Soccer", "name"].dropna().unique())


df = pd.read_csv("script/outputs/wsoc_aligned_gamedays.csv")

# Make sure your date column name matches this — change if necessary
# (e.g., "date", "game_date", or "test_date")
date_col = "date"  

# Convert to datetime safely
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

# Filter for 2024 and extract unique dates
unique_2024_dates = sorted(df.loc[df[date_col].dt.year == 2024, date_col].dropna().unique())

print("Unique 2024 dates:")
for d in unique_2024_dates:
    print(d.date())