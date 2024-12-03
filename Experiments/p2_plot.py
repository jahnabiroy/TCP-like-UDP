import pandas as pd
import matplotlib.pyplot as plt

# Read data from CSV file
data = pd.read_csv("p2_fairness_final.csv")

# Grouping the data by 'delay' and calculating the mean
grouped_data = data.groupby("delay")[["ttc1", "ttc2", "jfi"]].mean()

# Extracting the grouped columns
delay = grouped_data.index
ttc1_mean = grouped_data["ttc1"]
ttc2_mean = grouped_data["ttc2"]
jfi_mean = grouped_data["jfi"]

print(grouped_data)

# Create a figure with two subplots
plt.figure(figsize=(12, 5))

# First subplot for TTC values
plt.subplot(1, 2, 1)
plt.plot(delay, ttc1_mean, label="TTC1", marker="o", color="b")
plt.plot(delay, ttc2_mean, label="TTC2", marker="o", color="r")
plt.xlabel("Delay")
plt.ylabel("TTC Values")
plt.title("TTC1 and TTC2 vs Delay")
plt.legend()
plt.grid(True)

# Second subplot for JFI
plt.subplot(1, 2, 2)
plt.plot(delay, jfi_mean, label="JFI", marker="x", color="g")
plt.xlabel("Delay")
plt.ylabel("JFI Value")
plt.title("JFI vs Delay")
plt.legend()
plt.grid(True)

# Adjust layout to prevent overlap
plt.tight_layout()

# Save the figure
plt.savefig("p2_plots.png")
plt.close()
