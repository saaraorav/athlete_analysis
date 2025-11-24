import pandas as pd
import numpy as np
from pathlib import Path

# --- Folder path ---
minutesplayed_2025 = pd.read_csv("../raw_data/Soccer2025_minutesplayed.csv")
minutesplayed_2024 = pd.read_csv("../raw_data/Soccer2024_minutesplayed.csv")

def fix_name_format(df):
    df['athlete_name'] = (
        df['athlete_name']
        .astype(str)
        .str.split(',', n=1)                      # split into [lastname, firstname]
        .apply(lambda x: f"{x[1].strip()} {x[0].strip()}" if len(x) == 2 else x[0])
    )
    return df

# Apply to both tables
minutesplayed_2024 = fix_name_format(minutesplayed_2024)
minutesplayed_2025 = fix_name_format(minutesplayed_2025)

# unique_athletes = sorted(minutesplayed_2024['athlete_name'].dropna().unique().tolist())
# print(unique_athletes)
# print("Total unique athletes:", len(unique_athletes))

# unique_athletes = sorted(minutesplayed_2025['athlete_name'].dropna().unique().tolist())
# print(unique_athletes)
# print("Total unique athletes:", len(unique_athletes))


minutesplayed_2024['date'] = pd.to_datetime(minutesplayed_2024['date'], errors='coerce')

# Format as YYYY-MM-DD
minutesplayed_2024['date'] = minutesplayed_2024['date'].dt.strftime('%Y-%m-%d')

minutesplayed_all = pd.concat([minutesplayed_2024, minutesplayed_2025], ignore_index=True)

# 2️Make sure date is datetime
minutesplayed_all['date'] = pd.to_datetime(minutesplayed_all['date'], errors='coerce')

# 3️Sort by date (descending → most recent first)
minutesplayed_all = minutesplayed_all.sort_values('date', ascending=False).reset_index(drop=True)

# print(minutesplayed_2024.head(10))

output_path = "../clean_data/minutesplayed_clean.csv"
minutesplayed_all.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")
