# run_lomb_scargle.py
# in this script we will play around with running LS using the astropy functions and plotting said results...
# we are running LS with a false alarm probability to generate some p-values.

import argparse
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from astropy.timeseries import LombScargle

# start the function to run LS for each individual
def process_individual(df_subset):
    """Runs Lomb-Scargle and returns both stats and periodogram plotting data."""
    t = df_subset['ZT_continuous'].values # grab time
    y = df_subset['filtered_distance'].values # grab distance bins
    
    # 1. survival check (must have at least 48 hours of data)
    time_span = t.max() - t.min()
    if time_span < 48.0:
        return None, None
        
    # 2. define the range of periods to search (16 to 32 hours) 
    periods = np.linspace(16.0, 32.0, 1000)
    freqs = 1.0 / periods
    
    # 3. initialize and run lomb-scargle
    ls = LombScargle(t, y, normalization='standard') # normalization = "standard"
    power = ls.power(freqs)
    
    # 4. extract peak metrics
    best_idx = np.argmax(power)
    peak_period = periods[best_idx]
    peak_power = power[best_idx]
    
    # start statistics
    # calculate the exact p-value of this specific aphid's peak frequency's power
    p_value = float(ls.false_alarm_probability(peak_power))
    
    # calculate the power threshold required to achieve p = 0.05 (for plotting)
    # FIX: removed the [0] because Astropy returns a single float here!
    fap_05_threshold = float(ls.false_alarm_level(0.05))
    
    # boolean flag based on alpha = 0.05
    is_rhythmic = bool(p_value < 0.05)

    # stats dictionary
    stats = {
        'time_span_hours': time_span,
        'peak_period': peak_period,
        'peak_power': peak_power,
        'p_value': p_value,
        'fap_05_threshold': fap_05_threshold,
        'is_rhythmic': is_rhythmic,
        'error': "None"
    }
    
    # 5. create a dataframe of the curve for plotting later
    periodogram_df = pd.DataFrame({
        'period': periods,
        'power': power,
        'peak_period': peak_period,
        'peak_power': peak_power,
        'fap_05_threshold': fap_05_threshold
    })
    
    return stats, periodogram_df

# making a function that can show us the FAP power thresholds on our plots.

def draw_periodogram_thresholds(data, **kwargs):
    """Custom Seaborn mapping function to draw thresholds and peaks on each facet."""
    ax = plt.gca()
    if data.empty: return
    
    # draw the p=0.05 significance line
    thresh = data['fap_05_threshold'].iloc[0]
    ax.axhline(thresh, color='red', linestyle='--', linewidth=1.5, alpha=0.8, zorder=1)
    
    # plot a gold star on the highest peak
    peak_period = data['peak_period'].iloc[0]
    peak_power = data['peak_power'].iloc[0]
    ax.plot(peak_period, peak_power, marker='*', color='gold', markersize=10, markeredgecolor='black', zorder=3)
    
    # add a small text label for the period
    ax.text(peak_period + 0.5, peak_power, f"{peak_period:.1f}h", fontsize=9, va='center')

# start main function

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_in", required=True)
    parser.add_argument("--out_dir", required=True, help="Directory to save the CSV and Plots.")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    print(f"Loading data from {args.csv_in}...")
    df = pd.read_csv(args.csv_in)

    stats_results = []
    periodogram_results = []
    
    grouped = df.groupby(['treatment', 'replicate', 'individual'])
    print(f"Found {len(grouped)} unique individuals. Running Lomb-Scargle and calculating p-values...")
    
    for (treatment, replicate, individual), group_df in grouped:
        group_df = group_df.sort_values('ZT_continuous')
        stats, pg_df = process_individual(group_df)
        
        if stats is not None:
            # add identifiers
            for d in [stats, pg_df]:
                d['treatment'] = treatment
                d['replicate'] = replicate
                d['individual'] = individual
                
            stats_results.append(stats)
            periodogram_results.append(pg_df)
            
    if not stats_results:
        print("No individuals met the 48-hour survival minimum for analysis.")
        return

    # save the statistics as a csv for each individual
    stats_df = pd.DataFrame(stats_results)
    cols = ['treatment', 'replicate', 'individual', 'time_span_hours', 
            'is_rhythmic', 'p_value', 'peak_period', 'peak_power', 'fap_05_threshold']
    stats_df = stats_df[cols]
    
    csv_out = os.path.join(args.out_dir, "Lomb_Scargle_Stats.csv")
    stats_df.to_csv(csv_out, index=False)
    
    # starting a faceted plot
    print("Generating Faceted Periodogram Plots (This may take a minute)...")
    all_pg_df = pd.concat(periodogram_results, ignore_index=True)
    
    sns.set_theme(style="whitegrid")
    g = sns.FacetGrid(
        all_pg_df, 
        col="individual", 
        row="replicate", 
        hue="treatment",
        margin_titles=True, 
        height=2.5, 
        aspect=1.2
    )
    
    # map the core line plot
    g.map_dataframe(sns.lineplot, x="period", y="power", linewidth=1.5, zorder=2)
    
    # add our custom threshold line and peak stars
    g.map_dataframe(draw_periodogram_thresholds)
    
    g.set_axis_labels("Period (Hours)", "Lomb-Scargle Power")
    
    # safely handle y-axis limits (preventing NaN crashes)
    max_power = all_pg_df['power'].max()
    max_power = max_power if not pd.isna(max_power) else 1.0
    g.set(xlim=(16, 32), ylim=(0, max_power * 1.2)) # Add 20% headroom for the star label
    
    g.fig.subplots_adjust(top=0.9)
    g.fig.suptitle('Lomb-Scargle Periodograms (Red Line = p<0.05)', fontsize=16)
    
    plot_out = os.path.join(args.out_dir, "Periodograms_Faceted.png")
    plt.savefig(plot_out, dpi=300, bbox_inches='tight')
    plt.close()

    # summarize everything in a print statement, format for the cli
    print("\n--- RHYTHMICITY SUMMARY (p < 0.05) ---")
    summary = stats_df.groupby('treatment')['is_rhythmic'].mean() * 100
    for treat, pct in summary.items():
        print(f"{treat}: {pct:.1f}% of individuals showed significant rhythms.")
    print(f"\nSaved statistics to: {csv_out}")
    print(f"Saved plots to: {plot_out}")

if __name__ == "__main__":
    main()