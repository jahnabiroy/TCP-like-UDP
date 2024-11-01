import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# Read data from CSV file
def plot(filename1, filename2, column):
    data1 = pd.read_csv(f"{filename1}.csv")
    data2 = pd.read_csv(f"{filename2}.csv")
    if column == "delay":
        data2 = data2[data2["ttc"] <= 10]
    elif column == "loss":
        data2 = data2[data2["ttc"] <= 20]

    # Separate data based on fast_recovery
    p2_loss = data1.groupby(f"{column}", as_index=False)["ttc"].mean()
    p2_loss["throughput"] = 800 / p2_loss["ttc"]
    if column == "loss":
        p2_loss["packet_loss_square_root"] = np.sqrt(p2_loss["loss"])
    print(p2_loss)

    # if column == "delay":
    #     p1_loss = (
    #         data2[data2["fast_recovery"] == 1]
    #         .groupby(f"{column}", as_index=False)["ttc"]
    #         .mean()
    #     )

    # Plot the data
    plt.figure(figsize=(10, 6))

    # Plot for fast_recovery == True
    if column == "loss":
        plt.plot(
            p2_loss["packet_loss_square_root"],
            p2_loss["throughput"],
            label=f"P2 sqrt({column})",
            marker="o",
        )
    else:
        plt.plot(
            p2_loss[f"{column}"],
            p2_loss["throughput"],
            label=f"P2 {column}",
            marker="o",
        )

    # # Plot for fast_recovery == False
    # plt.plot(
    #     p1_loss[f"{column}"],
    #     p1_loss["ttc"],
    #     label=f"P1 {column}",
    #     marker="x",
    # )

    # Adding labels and title

    plt.ylabel("Average Throughput (Mbps)")
    if column == "loss":
        plt.xlabel(f"sqrt({column})")
        plt.title(f"Average Throughput vs sqrt({column})")
    else:
        plt.xlabel(f"{column}")
        plt.title(f"Average Throughput vs {column}")

    # Display legend
    plt.legend()

    # Show the plot
    plt.grid(True)
    plt.savefig(f"p3_{column}_plot_thru.png")


plot("p3_delay", "reliability_delay", "delay")
plot("p3_loss", "reliability_loss", "loss")
