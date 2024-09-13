import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import glob
import os

def drawResults(data_folder):
    # Get all CSV files in the data folder
    csv_files = glob.glob(os.path.join(data_folder, '*.csv'))

    # Initialize an empty DataFrame to store all data
    all_data = pd.DataFrame()

    # Read and combine all CSV files
    for file_path in csv_files:
        df = pd.read_csv(file_path)
        df['Time'] = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M:%S', errors='coerce')
        all_data = pd.concat([all_data, df], ignore_index=True)

    # Sort data by time
    all_data = all_data.sort_values('Time')

    # Check if 'ChlAdj' column exists
    chl_adj_col = next((col for col in all_data.columns if 'ChlAdj' in col), None)
    if not chl_adj_col:
        print("Error: 'ChlAdj' column not found in the CSV files.")
        print("Available columns:", all_data.columns.tolist())
        return

    # Set the style to a built-in Matplotlib style
    plt.style.use('ggplot')

    # Calculate moving average and standard deviation
    window = 4*12  # 24 hours, 4 data points per hour
    all_data['MA'] = all_data[chl_adj_col].rolling(window=window, center=True).mean()
    all_data['STD'] = all_data[chl_adj_col].rolling(window=window, center=True).std()

    # Calculate percentile bands
    all_data['Lower_Percentile'] = all_data[chl_adj_col].rolling(window=window, center=True).quantile(0.25)
    all_data['Upper_Percentile'] = all_data[chl_adj_col].rolling(window=window, center=True).quantile(0.75)

    # Create the plot
    fig, ax = plt.subplots(figsize=(16, 10))

    # Plot raw data
    ax.scatter(all_data['Time'], all_data[chl_adj_col], alpha=0.3, s=2, color='#1f77b4', label='Raw Data')

    # Plot moving average
    ax.plot(all_data['Time'], all_data['MA'], color='#d62728', linewidth=2, label='12-hour Moving Average')

    # Plot standard deviation bands
    ax.fill_between(all_data['Time'], all_data['MA'] - all_data['STD'], 
                    all_data['MA'] + all_data['STD'], alpha=0.2, color='#ff7f0e', 
                    label='±1 Std Dev')

    # Plot percentile bands
    ax.fill_between(all_data['Time'], all_data['Lower_Percentile'], 
                    all_data['Upper_Percentile'], alpha=0.2, color='#2ca02c', 
                    label='25th-75th Percentile')

    # Set title and labels
    ax.set_title('Chlorophyll Adjusted (ChlAdj) Time Series Analysis', fontsize=20, pad=20)
    ax.set_xlabel('Time', fontsize=14, labelpad=10)
    ax.set_ylabel('ChlAdj', fontsize=14, labelpad=10)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    # Rotate and align the tick labels so they look better
    plt.gcf().autofmt_xdate()

    # Set y-axis limits to focus on the main data range
    y_min, y_max = np.percentile(all_data[chl_adj_col], [1, 99])
    ax.set_ylim(y_min, y_max)

    # Improve legend
    ax.legend(loc='upper right', fontsize=12, framealpha=0.9)

    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Adjust layout
    plt.tight_layout()

    # Save the plot as a PNG file in the input directory
    output_file = os.path.join(data_folder, 'chlorophyll_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"Analysis complete. Graph saved as {output_file}")

    # Print some statistics about the data
    print("\nData Statistics:")
    print(all_data[chl_adj_col].describe())

    # Check for NaN values in calculated columns
    print("\nNaN count in calculated columns:")
    print(all_data[['MA', 'STD', 'Lower_Percentile', 'Upper_Percentile']].isna().sum())

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python drawResults.py <data_folder_path>")
    else:
        data_folder = sys.argv[1]
        drawResults(data_folder)