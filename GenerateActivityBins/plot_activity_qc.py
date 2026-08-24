# plot_activity_qc.py

# in this script we will generate some plots that can qc our 1 minute bins generated in generate_activity_bins.py

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# everything is in def main()
# provide the following cl arguments when running script

def main():
    parser = argparse.ArgumentParser(description="Generate QC plots for 96h Activity Data.") # function description
    parser.add_argument("--csv_in", required=True, help="Path to the 1-min binned activity CSV.") # the path to the csv
    parser.add_argument("--out_dir", required=True, help="Directory to save the QC plots.") # output dir
    parser.add_argument("--px_per_cm", type=float, default=281.0, help="Pixels per cm conversion factor.") # the FIJI generated scale in mm. i.e., px to mm.
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    print(f"Loading data from {args.csv_in}...")
    df = pd.read_csv(args.csv_in)
    
    # 1. convert pixels to cm
    df['distance_cm'] = df['filtered_distance'] / args.px_per_cm
    
    #  Some quick qc checks (formatted for looking ok when printed to console)
    print("\n--- DATA SANITY CHECKS ---")
    max_dist = df['distance_cm'].max()
    print(f"Maximum distance moved in a single minute: {max_dist:.2f} cm")
    
    if max_dist > 40:
        # use emoji for good visual diagnostic, and format for the cli
        print("🚨 WARNING: Max distance exceeds biological probability (>40 cm/min).")
        print("This indicates 'teleportation' artifacts. Check QC_1_Distance_Histogram.png!")
    else:
        print("✅ Max distance looks biologically feasible. But be sure to double check the QC plots.")
        
    global_active_pct = (df['is_active'].sum() / len(df)) * 100
    print(f"Global Activity Level: Aphids were moving {global_active_pct:.1f}% of the time.")
    print("--------------------------\n")

    sns.set_theme(style="whitegrid")

    # now we can generate some plots that will further provide qc
   
    # plot 1: distance histogram (all bouts non-log scale)
    
    print("Generating Distance Histogram...")
    # adjust as needed for publication
    plt.figure(figsize=(10, 6))
    
    # we now plot the full dataset including 0s. 
    # we can apply a log scale to the Y-axis so the massive '0' bin doesn't squash the active data. in normal scale for now 
    sns.histplot(data=df, x='distance_cm', bins=100, color='purple')
    #plt.yscale('log')
    
    # simple line showing median
    plt.axvline(df['distance_cm'].median(), color='red', linestyle='--', label=f"Median: {df['distance_cm'].median():.2f} cm")
    
    plt.title("Distribution of Distance Travelled per Minute", fontsize=14)
    plt.xlabel("Distance Travelled (cm / min)", fontsize=12)
    plt.ylabel("Frequency (Number of 1-min bins)", fontsize=12)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(args.out_dir, "QC_1_Distance_Histogram.png"), dpi=300)
    plt.close()


    # plot 2: faceted actogram timeline, with 30 minute mean activity bins
    print("Generating Faceted Timeline...")
    
    # aggregate to 30-min chunks for visual clarity
    df['ZT_30min'] = (df['ZT_continuous'] * 2).round() / 2
    df_30min = df.groupby(['treatment', 'replicate', 'individual', 'ZT_30min'])['distance_cm'].mean().reset_index()

    # create a FacetGrid (rows = replicates, columns = individuals)
    g = sns.FacetGrid(
        df_30min, 
        col="individual", 
        row="replicate", 
        hue="treatment", 
        margin_titles=True, 
        height=2.5, 
        aspect=1.5
    )
    
    g.map_dataframe(sns.lineplot, x="ZT_30min", y="distance_cm", linewidth=1.5)
    
    # add night shading on every individual subplot
    for ax in g.axes.flat:
        max_zt = df_30min['ZT_30min'].max()
        if not pd.isna(max_zt):
            for zt_start in np.arange(12, max_zt, 24):
                ax.axvspan(zt_start, zt_start + 12, color='grey', alpha=0.2, lw=0)

    g.set_axis_labels("Continuous ZT (Hours)", "Mean Dist (cm/min)")
    g.fig.subplots_adjust(top=0.9)
    g.fig.suptitle('Individual Aphid Locomotion Profiles (30-min Mean)', fontsize=16)
    g.add_legend(title="Treatment")
    plt.savefig(os.path.join(args.out_dir, "QC_2_Faceted_Timeline.png"), dpi=300, bbox_inches='tight')
    plt.close()


    # plot 3: tracking coverage histogram

    print("Generating Coverage Histogram...")
    plt.figure(figsize=(8, 5))
    sns.histplot(data=df, x='tracking_coverage', bins=50, color='teal')
    plt.title("SLEAP Track Coverage per 1-Minute Bin")
    plt.xlabel("Coverage Fraction (1.0 = 100% of frames tracked)")
    plt.ylabel("Number of Bins")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out_dir, "QC_3_Tracking_Coverage.png"), dpi=300)
    plt.close()

    

    # plot 4: circadian actogram facet grid (vertical lines)

    print("Generating Unbinned 1-Minute Impulse Actogram Grid...")

    g_raw = sns.FacetGrid(
        df, 
        col="individual", 
        row="replicate", 
        hue="treatment", 
        margin_titles=True, 
        height=2.5, 
        aspect=1.5
    )
    
    # custom mapping function using vlines for actigraphy spike rendering
    def plot_actogram_spikes(data, x_col, y_col, color, **kwargs):
        ax = plt.gca()
        x = data[x_col].values
        y = data[y_col].values
        # draw vertical lines from y=0 up to y=distance for each minute
        ax.vlines(x=x, ymin=0, ymax=y, colors=color, linewidth=0.6, alpha=0.95)

    g_raw.map_dataframe(plot_actogram_spikes, x_col="ZT_continuous", y_col="distance_cm")
    
    # add night shading across all panels
    for ax in g_raw.axes.flat:
        max_zt = df['ZT_continuous'].max()
        if not pd.isna(max_zt):
            for zt_start in np.arange(12, max_zt, 24):
                ax.axvspan(zt_start, zt_start + 12, color='grey', alpha=0.25, lw=0)
        
        ax.set_xticks([0, 24, 48, 72, 96])
        ax.set_ylim(bottom=0)  # pin baseline to 0

    g_raw.set_axis_labels("Continuous ZT (Hours)", "Raw Dist (cm/min)")
    g_raw.fig.subplots_adjust(top=0.9)
    g_raw.fig.suptitle('Individual Aphid Actogram Profiles (1-min Impulse Raster)', fontsize=16)
    g_raw.add_legend(title="Treatment")
    
    plt.savefig(os.path.join(args.out_dir, "QC_4_Unbinned_Faceted_Timeline.png"), dpi=300, bbox_inches='tight')
    plt.close()

    
    # plot 5: Filled Step Actogram Grid (fill_between)

    print("Generating Unbinned 1-Minute Filled Step Actogram Grid...")

    g_raw = sns.FacetGrid(
        df, 
        col="individual", 
        row="replicate", 
        hue="treatment", 
        margin_titles=True, 
        height=2.5, 
        aspect=1.5
    )
    
    def plot_step_fill(data, x_col, y_col, color, **kwargs):
        ax = plt.gca()
        # ssort values to ensure step progression is continuous
        data_sorted = data.sort_values(by=x_col)
        x = data_sorted[x_col].values
        y = data_sorted[y_col].values
        
        # fill under stepped line
        ax.fill_between(x, 0, y, step='post', color=color, alpha=0.85, lw=0)

    g_raw.map_dataframe(plot_step_fill, x_col="ZT_continuous", y_col="distance_cm")
    
    # add night shading across all panels
    for ax in g_raw.axes.flat:
        max_zt = df['ZT_continuous'].max()
        if not pd.isna(max_zt):
            for zt_start in np.arange(12, max_zt, 24):
                ax.axvspan(zt_start, zt_start + 12, color='grey', alpha=0.25, lw=0)
        
        ax.set_xticks([0, 24, 48, 72, 96])
        ax.set_ylim(bottom=0)

    g_raw.set_axis_labels("Continuous ZT (Hours)", "Raw Dist (cm/min)")
    g_raw.fig.subplots_adjust(top=0.9)
    g_raw.fig.suptitle('Individual Aphid Actogram Profiles (1-min Filled Step)', fontsize=16)
    g_raw.add_legend(title="Treatment")
    
    plt.savefig(os.path.join(args.out_dir, "QC_5_Filled_step_acrogram.png"), dpi=300, bbox_inches='tight')
    plt.close()


    print(f"Success! QC plots saved to: {args.out_dir}")

if __name__ == "__main__":
    main()