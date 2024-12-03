import matplotlib.pyplot as plt

# Data for plotting
loss_percent = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
throughput_mbps = [
    0.49,
    0.412,
    0.49,
    0.416,
    0.264,
    0.488,
    0.416,
    0.236,
    0.318,
    0.408,
    0.336,
]

# Create the plot
plt.figure(figsize=(10, 6))
plt.plot(loss_percent, throughput_mbps, marker="o", color="r", linestyle="-")
plt.title("Throughput vs Loss")
plt.xlabel("Loss (%)")
plt.ylabel("Throughput (Mbps)")
plt.grid(True)

# Show plot
plt.show()
