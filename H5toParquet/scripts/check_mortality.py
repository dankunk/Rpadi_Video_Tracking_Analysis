# check_mortality.py
# This script checks the mortality of each aphid in one master parquet video. 
# quality control to see if our snakemake pipeline is working properly. 
# we can match back to the original mortality data to see if things are looking as they would expect.

import argparse
import pandas as pd
import matplotlib.pyplot as plt

def main():
    parser = argparse.ArgumentParser(description="Check mortality masking in master parquet.")
    parser.add_argument("--parquet_in", required=True, help="Path to the master parquet file")
    args = parser.parse_args()

    print(f"Loading {args.parquet_in}...")
    
    # Load global_frame instead of elapsed_hours
    df = pd.read_parquet(args.parquet_in, columns=['individual', 'global_frame'], engine='pyarrow')

    # Calculate elapsed_hours on the fly (60 fps = 216,000 frames per hour)
    df['elapsed_hours'] = df['global_frame'] / 216000.0

    # Group by individual and find the maximum elapsed hour (their time of death / end of tracking)
    summary = df.groupby('individual')['elapsed_hours'].max().reset_index()
    summary = summary.rename(columns={'elapsed_hours': 'Lifespan (Hours)'})

    # Print the table to the console
    print("\n--- Mortality Check Summary ---")
    print(summary.to_string(index=False))
    print("-------------------------------\n")

    # Plot the results
    plt.figure(figsize=(10, 6))
    
    # Create a bar chart
    bars = plt.bar(summary['individual'].astype(str), summary['Lifespan (Hours)'], color='teal', edgecolor='black')
    
    # Add a red dashed line at 96 hours (the expected max duration)
    plt.axhline(y=96, color='red', linestyle='--', label='End of Experiment (96h)')
    
    # Formatting
    plt.xlabel('Individual Aphid ID', fontsize=12)
    plt.ylabel('Total Hours Tracked', fontsize=12)
    plt.title(f'Lifespan of Aphids\n{args.parquet_in.split("/")[-1]}', fontsize=14)
    plt.ylim(0, 105) # Cap Y-axis slightly above 96 for visibility
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Show plot, close window to finish script execution
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()