import pandas as pd
import matplotlib.pyplot as plt

# Read data from CSV file
data = pd.read_csv('p2_fairness.csv')  # Replace 'your_file.csv' with your actual file name

# Grouping the data by 'delay' and calculating the mean for only 'ttc1', 'ttc2', and 'jfi'
grouped_data = data.groupby('delay')[['ttc1', 'ttc2', 'jfi']].mean()

# Extracting the grouped columns
delay = grouped_data.index
ttc1_mean = grouped_data['ttc1']
ttc2_mean = grouped_data['ttc2']
jfi_mean = grouped_data['jfi']

# Plotting
plt.figure(figsize=(10, 6))

# Plotting mean ttc1 and ttc2
plt.plot(delay, ttc1_mean, label="TTC1 Mean", marker='o', color='b')
plt.plot(delay, ttc2_mean, label="TTC2 Mean", marker='o', color='r')

# Plotting JFI mean
plt.plot(delay, jfi_mean, label="JFI Mean", marker='x', color='g')

# Adding labels and title
plt.xlabel("Delay")
plt.ylabel("Mean Values")
plt.title("Mean TTC1, TTC2, and JFI vs Delay")
plt.legend()

# Show plot
plt.grid(True)
plt.savefig("p2_plot.png")
