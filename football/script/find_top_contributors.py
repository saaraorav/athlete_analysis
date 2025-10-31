import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
# import numpy as np

catapult_data = pd.read_csv("../clean_data/catapult_data_practice_game_clean.csv")

# --- Make sure date column is datetime ---
catapult_data["date"] = pd.to_datetime(catapult_data["date"], errors="coerce")

# --- Extract year ---
catapult_data["year"] = catapult_data["date"].dt.year

# --- Filter only game activities ---
games = catapult_data[catapult_data["activity"].str.lower() == "game"].copy()

# --- Compute per-athlete yearly totals ---
yearly_load = (
    games.groupby(["year", "athlete_name"], as_index=False)
         .agg(total_load_sum=("total_player_load", "sum"),
              game_count=("total_player_load", "count"))
)

# --- Compute average load per game ---
yearly_load["avg_load_per_game"] = yearly_load["total_load_sum"] / yearly_load["game_count"]

# --- Get top 10 athletes per year ---
top10_per_year = (
    yearly_load.sort_values(["year", "avg_load_per_game"], ascending=[True, False])
                .groupby("year")
                .head(10)
                .reset_index(drop=True)
)

# --- Clean final table ---
final_table = top10_per_year[["year", "athlete_name", "avg_load_per_game"]]

output_path = "../clean_data/top_contributors.csv"
final_table.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")