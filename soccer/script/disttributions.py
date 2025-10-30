import pandas as pd

def excel_to_date(serial, system='1900', as_string=False):
    """
    Convert an Excel serial date to a readable format.

    Parameters:
        serial (int or float): Excel serial date number
        system (str): '1900' (default for Windows Excel) or '1904' (Mac Excel)
        as_string (bool): If True, return as 'YYYY-MM-DD' string

    Returns:
        pd.Timestamp or str: Converted date
    """
    if system == '1900':
        date = pd.to_datetime(serial, unit='D', origin='1899-12-30')
    elif system == '1904':
        date = pd.to_datetime(serial, unit='D', origin='1904-01-01')
    else:
        raise ValueError("system must be '1900' or '1904'")

    return date.strftime('%Y-%m-%d') if as_string else date

print(excel_to_date(45546))             # 2024-09-11 00:00:00
print(excel_to_date(45546, as_string=True))  # '2024-09-11'

print(excel_to_date(45550)) 





import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
catapult_data = pd.read_csv("../clean_data/catapult_data_for_dist.csv")

catapult_data['date'] = pd.to_datetime(catapult_data['date'], errors='coerce')
print(catapult_data['date'].dt.year.value_counts().sort_index())

# Make sure date is datetime
catapult_data['date'] = pd.to_datetime(catapult_data['date'])

# Get the 3 most recent game dates
last_three_games = (
    catapult_data.loc[
        (catapult_data['activity'] == 'game') &
        (catapult_data['date'].dt.year == 2024),
        'date'
    ]
      .drop_duplicates()
      .tail(5)
      .tolist()
)

print("Last 3 game dates:", last_three_games)

# table with just game dates
games_df = catapult_data.loc[
    (catapult_data['date'].isin(last_three_games)) &
    (catapult_data['activity'] == 'game')
].copy()
# print(games_df.head(200))


plt.figure(figsize=(15, 6))

for date in sorted(last_three_games):
    subset = games_df.loc[games_df['date'] == date, 'meterage_per_minute']
    plt.hist(subset, bins=20, alpha=0.5, label=date.strftime('%Y-%m-%d'))

plt.xlabel("Meterage Per Minute")
plt.ylabel("Number of Athletes")
plt.title("Distribution of Meterage Per Minute")
plt.legend(title="Game Date")
plt.grid(True, alpha=0.3)
x_min, x_max = plt.xlim()                 # get axis limits
plt.xticks(np.arange(0, x_max + 20, 10))
plt.show()