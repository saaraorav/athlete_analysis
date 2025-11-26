"""
Find athletes that are present in CMJ data but missing in Catapult data,
and athletes that are present in Catapult data but missing in CMJ data.
"""

import pandas as pd

# Load cleaned data
print("Loading data...")
cmj_data = pd.read_csv("../clean_data/wide_cmj.csv")
catapult_data = pd.read_csv("../clean_data/catapult_data_practice_game_clean.csv")

# Get unique athletes from each dataset
cmj_athletes = set(cmj_data['name'].str.strip().unique())
catapult_athletes = set(catapult_data['athlete_name'].str.strip().unique())

print(f"\nTotal unique athletes in CMJ data: {len(cmj_athletes)}")
print(f"Total unique athletes in Catapult data: {len(catapult_athletes)}")

# Find discrepancies
missing_in_catapult = cmj_athletes - catapult_athletes
missing_in_cmj = catapult_athletes - cmj_athletes

print(f"\n{'='*60}")
print(f"ATHLETES IN CMJ BUT MISSING IN CATAPULT: {len(missing_in_catapult)}")
print(f"{'='*60}")
for athlete in sorted(missing_in_catapult):
    cmj_count = len(cmj_data[cmj_data['name'].str.strip() == athlete])
    print(f"  {athlete} ({cmj_count} jump tests)")

print(f"\n{'='*60}")
print(f"ATHLETES IN CATAPULT BUT MISSING IN CMJ: {len(missing_in_cmj)}")
print(f"{'='*60}")
for athlete in sorted(missing_in_cmj):
    catapult_count = len(catapult_data[catapult_data['athlete_name'].str.strip() == athlete])
    print(f"  {athlete} ({catapult_count} activities)")

# Create DataFrames for export
missing_catapult_df = pd.DataFrame({
    'athlete_name': sorted(missing_in_catapult),
    'cmj_test_count': [len(cmj_data[cmj_data['name'].str.strip() == athlete]) for athlete in sorted(missing_in_catapult)]
})

missing_cmj_df = pd.DataFrame({
    'athlete_name': sorted(missing_in_cmj),
    'catapult_activity_count': [len(catapult_data[catapult_data['athlete_name'].str.strip() == athlete]) for athlete in sorted(missing_in_cmj)]
})

# Save to CSV
missing_catapult_df.to_csv("../clean_data/missing_in_catapult.csv", index=False)
missing_cmj_df.to_csv("../clean_data/missing_in_cmj.csv", index=False)

print(f"\n✓ Results saved to:")
print(f"  - ../clean_data/missing_in_catapult.csv")
print(f"  - ../clean_data/missing_in_cmj.csv")

# Summary statistics
both_datasets = cmj_athletes & catapult_athletes
print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"Athletes in BOTH datasets: {len(both_datasets)}")
print(f"Athletes ONLY in CMJ: {len(missing_in_catapult)}")
print(f"Athletes ONLY in Catapult: {len(missing_in_cmj)}")
print(f"Total unique athletes across both: {len(cmj_athletes | catapult_athletes)}")
