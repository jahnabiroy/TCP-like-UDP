import pandas as pd
import matplotlib.pyplot as plt

# Read data from CSV file
def plot(filename,column):
    data = pd.read_csv(f'{filename}.csv')
    # Separate data based on fast_recovery
    fast_recovery_true = data[data['fast_recovery'] == 1].groupby(f'{column}', as_index=False)['ttc'].mean()
    fast_recovery_false = data[data['fast_recovery'] == 0].groupby(f'{column}', as_index=False)['ttc'].mean()

    # Plot the data
    plt.figure(figsize=(10, 6))

    # Plot for fast_recovery == True
    plt.plot(fast_recovery_true[f"{column}"], fast_recovery_true['ttc'], label='Fast Recovery: True', marker='o')

    # Plot for fast_recovery == False
    plt.plot(fast_recovery_false[f"{column}"], fast_recovery_false['ttc'], label='Fast Recovery: False', marker='x')

    # Adding labels and title
    plt.xlabel(f"{column}")
    plt.ylabel('TTC (Time to Completion)')
    plt.title(f'TTC vs {column} for Different Fast Recovery States')

    # Display legend
    plt.legend()

    # Show the plot
    plt.grid(True)
    plt.savefig(f"{filename}_plot.png")


plot("reliability_delay","delay")
plot("reliability_loss","loss")