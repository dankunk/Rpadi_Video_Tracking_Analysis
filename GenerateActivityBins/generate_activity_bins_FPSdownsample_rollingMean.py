# generate_activity_bins_FPSdownsample_rollingMean.py
# In this script we also downsample the data to 30 fps to further reduce high frequency noise... We also add a smoothing filter with rolling means... 
# We probably want this to run with fewer cores. 

import argparse
import glob
import os
import re
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

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
    
    raise ValueError(f"CRITICAL ERROR: Could not parse datetime from video_id: {video_id}.")

def process_single_file(file_path, orig_fps, target_fps, smooth_window, jitter_thresh, max_jump, bout_thresh):
    print(f"Processing: {Path(file_path).name}...")
    start_zt = get_start_zt(file_path)
    
    cols_to_load = ['x', 'y', 'individual', 'treatment', 'replicate', 'global_frame']
    df = pd.read_parquet(file_path, columns=cols_to_load, engine='pyarrow')
    df = df.sort_values(by=['treatment', 'replicate', 'individual', 'global_frame'])
    
    # downsample
    if target_fps < orig_fps:
        step = orig_fps // target_fps
        df = df[df['global_frame'] % step == 0].copy()
    else:
        target_fps = orig_fps

    # smooth coordinates (rolling median filter to remove high frequency jitter)
    group_cols = ['treatment', 'replicate', 'individual']
    if smooth_window > 1:
        # Min_periods=1 ensures we don't get NaNs at the start of tracks
        df['x'] = df.groupby(group_cols)['x'].transform(lambda s: s.rolling(smooth_window, center=True, min_periods=1).median())
        df['y'] = df.groupby(group_cols)['y'].transform(lambda s: s.rolling(smooth_window, center=True, min_periods=1).median())

    # calculate euclidian distance between frames with hypot()
    df['dx'] = df.groupby(group_cols)['x'].diff()
    df['dy'] = df.groupby(group_cols)['y'].diff()
    df['distance'] = np.hypot(df['dx'], df['dy']).fillna(0)
    
    # frame-level filters (although smoothing should help a lot, we additionally include our jitter, teleport, and bout filters...)
    df['filtered_distance'] = np.where(
        (df['distance'] < jitter_thresh) | (df['distance'] > max_jump), 
        0, 
        df['distance']
    )
    
    frames_per_minute = target_fps * 60
    # recalculate minute bins based on the original global frame rate so ZT aligns perfectly
    orig_frames_per_minute = orig_fps * 60
    df['minute_bin'] = df['global_frame'] // orig_frames_per_minute
    
    # aggregate data
    binned_df = df.groupby(
        ['treatment', 'replicate', 'individual', 'minute_bin']
    ).agg(
        filtered_distance=('filtered_distance', 'sum'),
        tracked_frames=('global_frame', 'count')
    ).reset_index()
    
    binned_df['tracking_coverage'] = binned_df['tracked_frames'] / frames_per_minute
    
    # now adding the bout level filters
    binned_df['filtered_distance'] = np.where(
        binned_df['filtered_distance'] < bout_thresh, 
        0, 
        binned_df['filtered_distance']
    )
    
    binned_df['is_active'] = (binned_df['filtered_distance'] > 0).astype(int)
    
    # setting proper ZT time
    binned_df['ZT_continuous'] = start_zt + (binned_df['minute_bin'] / 60.0)
    binned_df['ZT_day'] = binned_df['ZT_continuous'] % 24

    # return dataframe with 1 minute bins we just made above
    return binned_df


# start main function, 
def main():
    parser = argparse.ArgumentParser(description="Generate filtered, 1-minute activity bins.")
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--out_file", required=True)
    parser.add_argument("--orig_fps", type=int, default=60, help="Original framerate of video.")
    parser.add_argument("--target_fps", type=int, default=30, help="Downsample to this FPS. Use 60 for no downsampling.")
    parser.add_argument("--smooth_window", type=int, default=5, help="Rolling median window size (in frames). 1 to disable.")
    parser.add_argument("--jitter", type=float, default=3.0)
    parser.add_argument("--max_jump", type=float, default=50.0)
    parser.add_argument("--bout", type=float, default=76.0)
    parser.add_argument("--cores", type=int, default=8)
    
    args = parser.parse_args()
    master_files = glob.glob(os.path.join(args.input_dir, "*_master.parquet"))
    
    if not master_files:
        print(f"No files found in {args.input_dir}")
        return
        
    print(f"Found {len(master_files)} files. Starting processing...")
    
    all_binned_data = []
    with ProcessPoolExecutor(max_workers=args.cores) as executor:
        futures = [executor.submit(process_single_file, f, args.orig_fps, args.target_fps, args.smooth_window, args.jitter, args.max_jump, args.bout) for f in master_files]
        for future in futures:
            all_binned_data.append(future.result())

    final_master_df = pd.concat(all_binned_data, ignore_index=True)
    final_master_df = final_master_df.sort_values(by=['treatment', 'replicate', 'individual', 'minute_bin']).reset_index(drop=True)
    
    final_master_df.to_csv(args.out_file, index=False)
    print(f"Done! Saved to: {args.out_file}")

if __name__ == "__main__":
    main()