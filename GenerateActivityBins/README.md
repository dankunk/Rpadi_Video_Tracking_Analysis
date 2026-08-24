# Generate Activity Bins

In this directory we will process our master parquet files that have individuals assigned by ROI, been filtered by their time of death, and have a global frame count as generated in `H5toParquet`.

We have a python script that will do all of the work and generate a final CSV file containing all the activity data.

To run the script we will first activate our `rpadi-video-tracking-analysis` venv... 

```powershell
. "C:\Users\nalamlab\OneDrive - Colostate\NIFA_PROJECT\Obj2\Rpadi_Video_Tracking_Analysis\.venv\Scripts\activate.ps1"
```

Next we can run this script with the following command line arguments as the script entails:



```powershell
python ./generate_activity_bins.py --input_dir "..\H5toParquet\output\final" --out_file ".\diet_1min_activity.csv" --fps 60 --jitter 3.0 --max_jump 50 --bout 76.0 --cores 16 # --> conservative at first...

# jitter run at
```


After running the script we can qc the data and see if it looks ok...


```powershell
python ./plot_activity_qc.py --csv_in ".\diet_1min_activity.csv" --out_dir ".\QC_Plots" --px_per_cm 281
```


We should probably mull around in these results and qc them for a bit. but once we are good we can take these exact signals and do LS on them to see if their periodic.

```powershell
python .\run_lomb_scargle.py --csv_in .\diet_1min_activity.csv --outdir .\ls_test
```