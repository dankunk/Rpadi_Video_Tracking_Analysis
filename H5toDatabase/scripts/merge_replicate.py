# This script merges intermediate, hour-based parquet files into the full 96 hour long parquet file per video/experimental rep
# i.e., for our diet dataset, with 16 total videos (each video has 96 hour long video chunks), we should have 16 final parquets...

import argparse
import glob
import os
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--master_out", required=True)
    args = parser.parse_args()

    # Find all intermediate parquets for this replicate
    parquet_files = glob.glob(os.path.join(args.input_dir, "*.parquet"))
    
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {args.input_dir}")

    # Read and concatenate
    dfs = [pd.read_parquet(f, engine='pyarrow') for f in parquet_files]
    master_df = pd.concat(dfs, ignore_index=True)

    # Save the master database
    master_df.to_parquet(args.master_out, engine='pyarrow', compression='snappy', index=False)
    print(f"Successfully merged {len(parquet_files)} files into {args.master_out}")

if __name__ == "__main__":
    main()