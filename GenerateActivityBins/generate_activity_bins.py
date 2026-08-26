# generate_activity_bins.py
# Calculates 1-minute activity bins with min (i.e. frame to frame location jitter), max (i.e. a teleport filter for large, biologically unlikely distances moved), and bout (i.e. an aphid has to travel at least X distance or we zero out that minute) filters.

# generate_activity_bins.py
import argparse
import glob
import os
import re
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor # for running in parallel
from pathlib import Path

# function to grab the time from file name and subtract 8 to get ZT time as ZT0 is 8 am.

def get_start_zt(file_path):
    first_row = pd.read_parquet(file_path, columns=['video_id'], engine='pyarrow').iloc[0]
    video_id = str(first_row['video_id'])
    
    match = re.search(r'Camera0_(\d{8}_\d{6})', video_id)
    if match:
        dt_str = match.group(1)
        start_time = datetime.strptime(dt_str, "%Y%m%d_%H%M%S")
        hours_since_midnight = start_time.hour + (start_time.minute / 60) + (start_time.second / 3600)
        start_zt = hours_since_midnight - 8
        if start_zt < 0: start_zt += 24 
        return start_zt
    
    # loud failsafe: do not quietly assign ZT 0 to broken filenames
    raise ValueError(f"CRITICAL ERROR: Could not parse datetime from video_id: {video_id}. Cannot safely assign ZT time.")

# function to process each file, we can loop through this...
# filtering for what is mentioned above, providing file path and framerate (which is always 60).

def process_single_file(file_path, fps, jitter_thresh, max_jump, bout_thresh):
    print(f"Processing: {Path(file_path).name}...")
    start_zt = get_start_zt(file_path)
    
    cols_to_load = ['x', 'y', 'individual', 'treatment', 'replicate', 'global_frame']
    df = pd.read_parquet(file_path, columns=cols_to_load, engine='pyarrow')
    df = df.sort_values(by=['treatment', 'replicate', 'individual', 'global_frame'])
    
    # 1. using np.hypot for eucl distance, grouping first by individual, the rest are redundant
    group_cols = ['treatment', 'replicate', 'individual']
    df['dx'] = df.groupby(group_cols)['x'].diff()
    df['dy'] = df.groupby(group_cols)['y'].diff()
    df['distance'] = np.hypot(df['dx'], df['dy']).fillna(0)
    
    # 2. frame-level filters
    df['filtered_distance'] = np.where(
        (df['distance'] < jitter_thresh) | (df['distance'] > max_jump), 
        0, 
        df['distance']
    )
    
    frames_per_minute = fps * 60
    df['minute_bin'] = df['global_frame'] // frames_per_minute
    
    # 3. aggregate data AND calculate track coverage (i.e. what percent of the video do we have data for?)
    binned_df = df.groupby(
        ['treatment', 'replicate', 'individual', 'minute_bin']
    ).agg(
        filtered_distance=('filtered_distance', 'sum'),
        tracked_frames=('global_frame', 'count') # Counts rows present in the bin
    ).reset_index()
    
    # Track Coverage (0.0 to 1.0)
    binned_df['tracking_coverage'] = binned_df['tracked_frames'] / frames_per_minute
    
    # 4. bin-level filters (bout threshold). just to be safe...
    binned_df['filtered_distance'] = np.where(
        binned_df['filtered_distance'] < bout_thresh, 
        0, 
        binned_df['filtered_distance']
    )
    
    binned_df['is_active'] = (binned_df['filtered_distance'] > 0).astype(int)
    
    # 5. add ZT time calculated above. needed for plotting and sorting...
    binned_df['ZT_continuous'] = start_zt + (binned_df['minute_bin'] / 60.0)
    binned_df['ZT_day'] = binned_df['ZT_continuous'] % 24
    
    return binned_df

# the main function for our script.
# need to specify all options for the functions above and below when running from the command line...

def main():
    parser = argparse.ArgumentParser(description="Generate filtered, 1-minute activity bins (Distance travelled) per invididual.")
    parser.add_argument("--input_dir", required=True, help = "Input directory.") # dir containing all parquet files per video (1 file for all 96 hour based chunks)
    parser.add_argument("--out_file", required=True, help= "Output directory and file name csv") # output file for the sorted, timestamped in ZT time, and filtered, minute by minute data.
    parser.add_argument("--fps", type=int, default=60, help = "Framerate of video data.") # specify framerate, for our aphid data its always 60
    parser.add_argument("--jitter", type=float, default=3.0, help="Min px/frame. Resonable ranges are anywhere from 1.0 to 3.0. See SLEAP model evals for a good idea of model error/jitter...") # jitter pixel filter, # of pixels
    parser.add_argument("--max_jump", type=float, default=50.0, help="Max px/frame to clear teleportation.") # big jumps pixel filter, # of pixels.
    parser.add_argument("--bout", type=float, default=76.0, help="Min px/minute total (1 body length).") # bout length for each minute. # of pixels
    parser.add_argument("--cores", type=int, default=8, help="Number of CPU cores to utilize.") # for parallel computing... hence why we are using concurrent.futures
    
    args = parser.parse_args()
    master_files = glob.glob(os.path.join(args.input_dir, "*_master.parquet"))
    
    if not master_files:
        print(f"No files found in {args.input_dir}")
        return
        
    print(f"Found {len(master_files)} files. Starting processing...")
    
    all_binned_data = []
    with ProcessPoolExecutor(max_workers=args.cores) as executor:
        futures = [executor.submit(process_single_file, f, args.fps, args.jitter, args.max_jump, args.bout) for f in master_files]
        for future in futures:
            all_binned_data.append(future.result())

    final_master_df = pd.concat(all_binned_data, ignore_index=True)
    final_master_df = final_master_df.sort_values(by=['treatment', 'replicate', 'individual', 'minute_bin']).reset_index(drop=True)
    
    final_master_df.to_csv(args.out_file, index=False)
    print(f"Done! Saved to: {args.out_file}")

if __name__ == "__main__":
    main()