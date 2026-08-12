# merge_replicate.py 
# This script merges intermediate, hour-based parquet files into the full 96 hour long parquet file per video/experimental rep
# i.e., for our diet dataset, with 16 total videos (each video has 96 hour long video chunks), we should have 16 final parquets...

# update: stop the data when the aphid is dead. i.e. parse mortality tsv, fed as abs path in config file.

import argparse
import glob
import os
import re
import pandas as pd

def extract_start_frame(text):
    """Safely extracts the starting frame integer from ANY string, ignoring dates."""
    text = str(text).strip()
    
    # Find ALL instances of an underscore followed by number-number
    # (e.g., it will find '_11-17', '_10-3', AND '_5616000-5831999')
    matches = re.findall(r'_(\d+)-\d+', text)
    
    # We always want the LAST match in the string (the frame range, not the date!)
    if matches:
        return int(matches[-1]) 
    return 0 

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--master_out", required=True)
    parser.add_argument("--mortality_tsv", required=False, help="Path to mortality TSV for this replicate")
    args = parser.parse_args()

    # 1. Sort files numerically by their extracted start frame (Chronological Ingestion)
    parquet_files = glob.glob(os.path.join(args.input_dir, "*.parquet"))
    parquet_files = sorted(parquet_files, key=extract_start_frame)
    
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {args.input_dir}")

    # Read and concatenate
    dfs = [pd.read_parquet(f, engine='pyarrow') for f in parquet_files]
    master_df = pd.concat(dfs, ignore_index=True)

    # 2. Apply Mortality/Escape Mask from TSV (If provided AND not empty)
    if args.mortality_tsv and os.path.exists(args.mortality_tsv):
        print(f"Checking behavior mask from: {args.mortality_tsv}")
        
        # Load TSV data
        mort_df = pd.read_csv(args.mortality_tsv, sep='\t')
        
        # Keep ONLY rows that are Mortality or Escape
        # Using .isin() handles any slight variations in how Boris logs it. should be `Escape` though, but `Escaped` is in the notes in the tsv file. need to be sure to only use the proper tsv column and value.
        valid_categories = ['Mortality', 'Escape', 'Escaped']
        mort_df = mort_df[mort_df['Behavioral category'].isin(valid_categories) | mort_df['Behavior'].isin(['Mort', 'Esc'])]

        if mort_df.empty:
            print("No Mortality or Escape events found. All aphids survived! Skipping mask.")
        else:
            # Extract the individual ID from the "Subject" column
            mort_df['individual'] = mort_df['Subject'].astype(str).apply(lambda x: int(x.split('-')[-1]))
            
            # Extract the global start frame of the specific video they died in
            mort_df['video_start'] = mort_df['Media file name'].apply(extract_start_frame)
            
            # Calculate EXACT global frame of death (Video Start Frame + Local Image Index)
            mort_df['death_global_frame'] = mort_df['video_start'] + mort_df['Image index start'].fillna(0).astype(int)
            
            # If an individual logged multiple events (e.g., an escape attempt then a final escape), 
            # we sort and keep only the earliest frame so we don't accidentally keep bad data.
            mort_df = mort_df.sort_values('death_global_frame').drop_duplicates(subset=['individual'], keep='first')

            # Merge the death cutoff into the master dataframe
            master_df = master_df.merge(mort_df[['individual', 'death_global_frame']], on='individual', how='left')

            # FILTER: Keep row IF (death frame is NA/survived) OR (current frame <= exact death frame)
            mask = master_df['death_global_frame'].isna() | (master_df['global_frame'] <= master_df['death_global_frame'])
            
            rows_before = len(master_df)
            master_df = master_df[mask]
            rows_after = len(master_df)
            
            print(f"Mask filtering dropped {rows_before - rows_after:,} rows of data post-mortality/escape.")

            # Clean up the temporary column
            master_df = master_df.drop(columns=['death_global_frame'])

    # 3. Global Master Sort (Individual -> Continuous Time)
    master_df = master_df.sort_values(by=['individual', 'global_frame']).reset_index(drop=True)

    # Save the master database
    master_df.to_parquet(args.master_out, engine='pyarrow', compression='snappy', index=False)
    print(f"Successfully merged files into {args.master_out}")

if __name__ == "__main__":
    main()