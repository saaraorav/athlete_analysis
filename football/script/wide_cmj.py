import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


raw_cmj_data = pd.read_csv("../raw_data/MASTER_all_CMJmetrics.csv")
# raw_cmj_data = raw_cmj_data.sort_values('recordedUTC', ascending=False)
# print(raw_cmj_data['recordedUTC'].tail(5))
# ensure it's a datetime
raw_cmj_data['recordedUTC'] = pd.to_datetime(raw_cmj_data['recordedUTC'], utc=True, errors='coerce')

# Convert to month/day/year string and then back to datetime (no timezone)
raw_cmj_data['date'] = pd.to_datetime(
    raw_cmj_data['recordedUTC'].dt.strftime('%m/%d/%Y')
)

# filter the dataframe
filtered_cmj = raw_cmj_data[
    (raw_cmj_data['date'] >= '2023-06-01') &
    (raw_cmj_data['typeName'] == 'Football')
].copy()

# optional: reset index
filtered_cmj.reset_index(drop=True, inplace=True)

# print(filtered_cmj.head(10))

# make table wide with peak_power_bm
base_cols = ['date', 'athleteId', 'name', 'sex', 'dateOfBirth',
             'typeName', 'testType', 'testId']
base = filtered_cmj[base_cols].drop_duplicates()

# Step 2: extract "Peak Power / BM" values
pp = (
    filtered_cmj.loc[filtered_cmj['definition.name'] == 'Peak Power / BM',
                     ['testId', 'athleteId', 'meanVal']]
    .rename(columns={'meanVal': 'peak_power_bm'})
    .drop_duplicates(subset=['testId', 'athleteId'])
)

# Step 3: merge back into the main table
wide = base.merge(pp, on=['testId', 'athleteId'], how='left')

# Step 4: optionally keep a representative valueName
if 'valueName' in filtered_cmj.columns:
    vn = (
        filtered_cmj.groupby(['testId', 'athleteId'], as_index=False)['valueName']
        .first()
    )
    wide = wide.merge(vn, on=['testId', 'athleteId'], how='left')
else:
    wide['valueName'] = pd.NA

# Step 5: reorder columns
final_cols = ['date', 'athleteId', 'name', 'sex', 'dateOfBirth',
              'valueName', 'typeName', 'testType', 'testId', 'peak_power_bm']
wide = wide.reindex(columns=final_cols)

wide['date'] = pd.to_datetime(wide['date'], errors='coerce')
result = wide.sort_values('date').reset_index(drop=True)

output_path = "../clean_data/wide_cmj.csv"
wide.to_csv(output_path, index=False)
print(f"Saved merged file to: {output_path}")

# print(wide.head(10))