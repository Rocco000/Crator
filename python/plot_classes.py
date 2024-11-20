import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

csv_path = Path(input("Provide the CSV path:\n"))

if not csv_path.exists():
    raise FileNotFoundError(f"CSV file {csv_path} doesn't exists")

df = pd.read_csv(csv_path)

# Get macro-categories
macro_categories = df["macro_category"].value_counts()

colors = plt.cm.tab20.colors # A matplotlib colormap of 20 colors

# Plot the number of instances per macro-category
plt.figure(figsize=(10, 6))
bars = plt.bar(macro_categories.index, macro_categories.values, color= colors[:len(macro_categories)])
plt.title('Number of Instances per Macro-Category')
plt.xlabel('Macro-Category')
plt.ylabel('Count')
plt.xticks(rotation=45)
plt.tight_layout()

# Add the count on top of each bar
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval, int(yval), ha="center", va="bottom")

plt.savefig(f"{csv_path.parents[0].joinpath('macro_category_plot.png')}")
plt.show()

# Get micro-categories
micro_categories = df["micro_category"].value_counts()

for macro_category in df["macro_category"].unique():
    # Get all micro-categories for the given macro-category
    micro_counts = df[df['macro_category'] == macro_category]['micro_category'].value_counts()

    plt.figure(figsize=(10, 6))
    bars = plt.bar(micro_counts.index, micro_counts.values, color=plt.cm.Set3.colors[:len(micro_counts)])
    plt.title(f'Number of Instances per Micro-Category in {macro_category}')
    plt.xlabel('Micro-Category')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Add the count on top of each bar
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval, int(yval), ha="center", va="bottom")

    save_path = csv_path.parents[0].joinpath(f"{macro_category}_plot.png")
    plt.savefig(save_path)
    plt.show()

# Check for rows with empty or missing values
empty_rows = df[df.isnull().any(axis=1)]

if not empty_rows.empty:
    print("Rows with missing values:")
    print(empty_rows)
else:
    print("No missing values found.")


