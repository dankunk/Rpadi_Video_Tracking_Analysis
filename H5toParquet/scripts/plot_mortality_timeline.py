# plot_mortality_timeline.py

import argparse
import glob
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

def extract_rep_num(rep_string):
    """Extracts the integer from the replicate string for clean numerical sorting."""
    import re
    match = re.search(r'rep(\d+)', str(rep_string).lower())
    return int(match.group(1)) if match else 0

def main():
    parser = argparse.ArgumentParser(description="Generate timeline and statistical plots of aphid mortality.")
    parser.add_argument("--input_dir", required=True, help="Path to master parquets (e.g., output/final)")
    parser.add_argument("--output_img", default="mortality_timeline.svg", help="Filename to save the main plot")
    args = parser.parse_args()

    # 1. Gather all master parquets
    parquet_files = glob.glob(os.path.join(args.input_dir, "*_master.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No master parquet files found in {args.input_dir}")

    print(f"Found {len(parquet_files)} master files. Extracting lifespans...")

    # 2. Extract Data (ON-THE-FLY MATH UPDATE)
    data = []
    for f in parquet_files:
        # Load global_frame instead of elapsed_hours
        df = pd.read_parquet(f, columns=['individual', 'global_frame', 'treatment', 'replicate'], engine='pyarrow')
        
        # Calculate elapsed_hours on the fly (60 fps = 216,000 frames per hour)
        df['elapsed_hours'] = df['global_frame'] / 216000.0
        
        summary = df.groupby(['treatment', 'replicate', 'individual'])['elapsed_hours'].max().reset_index()
        data.append(summary)

    master_summary = pd.concat(data, ignore_index=True)
    master_summary = master_summary.rename(columns={'elapsed_hours': 'lifespan'})

    # 3. Clean and Prepare Data
    master_summary['rep_num'] = master_summary['replicate'].apply(extract_rep_num)
    master_summary['y_label'] = "Rep " + master_summary['rep_num'].astype(str) + " - Ind " + master_summary['individual'].astype(str)

    # Split into LD and DD datasets
    df_ld = master_summary[master_summary['treatment'].str.contains('LD', case=False, na=False)].copy()
    df_dd = master_summary[master_summary['treatment'].str.contains('DD', case=False, na=False)].copy()

    df_ld = df_ld.sort_values(by=['rep_num', 'individual'], ascending=[True, True]).reset_index(drop=True)
    df_dd = df_dd.sort_values(by=['rep_num', 'individual'], ascending=[True, True]).reset_index(drop=True)

    # Assign Exact Hex Colors
    color_ld = '#EE99AA'  # Light Red
    color_dd = '#994455'  # Dark Red

    
    # PART 1: TIMELINE PLOT (FACETED by LD and DD)
    
    print("Generating faceted timeline plot...")
    
    max_rows = max(len(df_ld), len(df_dd))
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, max(6, max_rows * 0.25)))

    def plot_panel(ax, df, color):
        y_positions = range(len(df))
        # Draw Lifespan line
        ax.hlines(y=y_positions, xmin=0, xmax=df['lifespan'], color=color, alpha=0.9, linewidth=2.5, zorder=2)
        # Draw End Dot
        ax.scatter(df['lifespan'], y_positions, color=color, s=45, zorder=3, edgecolors='black', linewidths=0.5)
        # FINISH LINE
        ax.axvline(x=96, color='black', linestyle='--', alpha=0.8, zorder=1)

        ax.set_yticks(y_positions)
        ax.set_yticklabels(df['y_label'], fontsize=9)
        ax.set_xticks([0, 24, 48, 72, 96])
        ax.set_xlim(-2, 100) 
        ax.set_ylim(len(df) - 0.5, -0.5)

        ax.set_xlabel('Elapsed Time (Hours)', fontsize=12, fontweight='bold')
        ax.grid(axis='x', linestyle=':', alpha=0.7, zorder=0)

        # Separator lines
        rep_shifts = df['rep_num'].drop_duplicates().index.tolist()
        for shift_idx in rep_shifts[1:]:
            ax.axhline(y=shift_idx - 0.5, color='grey', linestyle='-', linewidth=0.5, alpha=0.4)

    # Titles removed from individual panels
    plot_panel(ax1, df_ld, color_ld)
    plot_panel(ax2, df_dd, color_dd)

    # Legend at the top to distinguish the panels
    ld_patch = mpatches.Patch(color=color_ld, label='Light-Dark (LD)')
    dd_patch = mpatches.Patch(color=color_dd, label='Constant Dark (DD)')
    end_line = plt.Line2D([0], [0], color='black', linestyle='--', label='End of Experiment (96h)')
    
    fig1.legend(handles=[ld_patch, dd_patch, end_line], loc='upper center', 
                bbox_to_anchor=(0.5, 1.05), frameon=False, fontsize=11, ncol=3)
    
    fig1.tight_layout(w_pad=2.0)
    fig1.savefig(args.output_img, bbox_inches='tight')
    print(f"Timeline plot saved to: {args.output_img}")

    
    # PART 2: STATISTICAL WILCOXON TEST & BOXPLOT
    
    print("\nCalculating statistics and generating summary boxplot...")
    
    ld_data = df_ld['lifespan'].dropna()
    dd_data = df_dd['lifespan'].dropna()

    # Calculate Mann-Whitney U Test (Wilcoxon rank-sum)
    u_stat, p_val = stats.mannwhitneyu(ld_data, dd_data, alternative='two-sided')
    
    # Determine significance asterisks
    if p_val <= 0.0001: sig = '****'
    elif p_val <= 0.001: sig = '***'
    elif p_val <= 0.01: sig = '**'
    elif p_val <= 0.05: sig = '*'
    else: sig = 'ns'

    print(f"Stats -> LD Median: {ld_data.median():.2f}h | DD Median: {dd_data.median():.2f}h")
    print(f"Stats -> Wilcoxon test: U = {u_stat:.3f}, p-value = {p_val:.4e} ({sig})")

    fig2, ax_stat = plt.subplots(figsize=(4, 6))

    bplot = ax_stat.boxplot([ld_data, dd_data], positions=[0, 1], widths=0.5, 
                            patch_artist=True, showfliers=False, zorder=2)

    # Style the boxes with specific colors
    colors = [color_ld, color_dd]
    for patch, color in zip(bplot['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
        patch.set_edgecolor('black')
        patch.set_linewidth(1.5)

    # Make the medians, caps, and whiskers thicker and black TODO--> change linewidth to 2.0 for better visibility?
    for element in ['medians', 'whiskers', 'caps']:
        for item in bplot[element]:
            item.set(color='black', linewidth=1.5)

    # Overlay Individual Data Points (Jitter)
    ld_jitter = np.random.normal(0, 0.08, size=len(ld_data))
    dd_jitter = np.random.normal(1, 0.08, size=len(dd_data))
    
    ax_stat.scatter(ld_jitter, ld_data, color='black', alpha=0.4, s=25, zorder=3)
    ax_stat.scatter(dd_jitter, dd_data, color='black', alpha=0.4, s=25, zorder=3)

    # Draw the Significance Bracket
    y_max = max(ld_data.max(), dd_data.max())
    bracket_y = y_max + 3  
    bracket_h = 2          

    ax_stat.plot([0, 0, 1, 1], [bracket_y, bracket_y+bracket_h, bracket_y+bracket_h, bracket_y], 
                 lw=1.5, color='black')
    
    ax_stat.text(0.5, bracket_y + bracket_h + 0.5, sig, ha='center', va='bottom', 
                 color='black', fontsize=14, fontweight='bold')

    # Format the Stats Plot
    ax_stat.set_xticks([0, 1])
    ax_stat.set_xticklabels(['Light-Dark\n(LD)', 'Constant Dark\n(DD)'], fontsize=12, fontweight='bold')
    ax_stat.set_ylabel('Lifespan (Hours)', fontsize=12, fontweight='bold')
    
    # Exact Y-TICKS mapping the timeline plot
    ax_stat.set_yticks([0, 24, 48, 72, 96])
    
    # Keeps the dynamic height constraint for the bracket
    ax_stat.set_ylim(-2, bracket_y + bracket_h + 10) 
    ax_stat.grid(axis='y', linestyle=':', alpha=0.7, zorder=0)

    # Save Stats Plot 
    stats_out_filename = args.output_img.replace('.svg', '_stats.svg')
    fig2.tight_layout()
    fig2.savefig(stats_out_filename, bbox_inches='tight')
    print(f"Stats boxplot saved to: {stats_out_filename}\n")

if __name__ == "__main__":
    main()