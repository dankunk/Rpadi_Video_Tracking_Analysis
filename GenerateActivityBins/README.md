# Generate Activity Bins

In this directory we will process our master parquet files that have individuals assigned by ROI, been filtered by their time of death, and have a global frame count as generated in `H5toParquet`.

We have a python script that will do all of the work and generate a final CSV file containing all the activity data.

To run the script we will first activate our `rpadi-video-tracking-analysis` venv... 

```powershell
. "C:\Users\nalamlab\OneDrive - Colostate\NIFA_PROJECT\Obj2\Rpadi_Video_Tracking_Analysis\.venv\Scripts\activate.ps1"
```

Note that the location of this environment will change depending on your computer. You can create the same venv we are using here by grabbing the uv.lock and using uv sync.

More Information on this process can be found here. https://docs.astral.sh/uv/concepts/projects/sync/


##

Next we can run our script with the following command line arguments as the script entails:


```powershell
python ./generate_activity_bins.py --input_dir "..\H5toParquet\output\final" --out_file ".\diet_1min_activity.csv" --fps 60 --jitter 3.0 --max_jump 50 --bout 76.0 --cores 16 # --> conservative at first...
```

After running the script we can qc the data and see if it looks ok...

```powershell
python ./plot_activity_qc.py --csv_in ".\diet_1min_activity.csv" --out_dir ".\QC_Plots" --px_per_cm 281
```

These plots are then generated in the output directory specified (`QC_Plots`), we additionally pass the conversion from pixels to cm.

# Adjusting Filtering

We can additionally play around with some of these filters to see what works best...

```powershell
python generate_activity_bins.py --input_dir ../H5toParquet/output/final/ --out_file ./diet_1min_activity_5jitter_50jump_76bout.csv --cores 8 --jitter 5


python .\plot_activity_qc.py --csv_in .\diet_1min_activity_5jitter_50jump_76bout.csv --out_dir ./QC_Plots_5jitter
```
```
Loading data from .\diet_1min_activity_5jitter_50jump_76bout.csv...

--- DATA SANITY CHECKS ---
Maximum distance moved in a single minute: 17.22 cm
✅ Max distance looks biologically feasible. But be sure to double check the QC plots.
Global Activity Level: Aphids were moving 50.5% of the time.
--------------------------

Generating Distance Histogram...
Generating Faceted Timeline...
Generating Coverage Histogram...
Generating Unbinned 1-Minute Impulse Actogram Grid...
Generating Unbinned 1-Minute Filled Step Actogram Grid...
Success! QC plots saved to: ./QC_Plots_5jitter
```


Additionally, we may want to downsample our video. Since the original video was 60 fps and we inferenced at 60 fps a lot of that noise is comping just because our sampling is such high resolution Because we know that aphid movement isnt on that scale we can downsample and still get good tracking data with less noise. We can start with 30 FPS but can even go down as small as 15 fps... In this new script `generate_activity_bins_FPSdownsample_rollingMean.py` we do all the same things as before except now we additionally downsample and apply a rolling mean filter... We want to run this with less cores since it will now likely use a bit more system resources applying the filter.

Here we specify the original FPS (60) and the target FPS after downsampling. Additionally, we provide the length of the smoothing window in pixels and the same filters as before. Its wise to reduce the number of cores since we are now using a lot more memory with the smoothing window filter.

```powershell
python generate_activity_bins_FPSdownsample_rollingMean.py --input_dir "../H5toParquet/output/final/" --out_file "./diet_1min_activity_downsample_rollingMean.csv" --orig_fps 60 --target_fps 30 --smooth_window 5 --jitter 5.0 --max_jump 50.0 --bout 76.0 --cores 2

# runs in less than 5 minutes with cores = 2. Could probably go up to 4 (32 GB ram on my home machine).

# now running same qc plots as before...

python .\plot_activity_qc.py --csv_in .\diet_1min_activity_downsample_rollingMean.csv --out_dir ./QC_Plots_downsample_rollingMean
```
```
Loading data from .\diet_1min_activity_downsample_rollingMean.csv...

--- DATA SANITY CHECKS ---
Maximum distance moved in a single minute: 16.55 cm
✅ Max distance looks biologically feasible. But be sure to double check the QC plots.
Global Activity Level: Aphids were moving 44.6% of the time.
--------------------------

Generating Distance Histogram...
Generating Faceted Timeline...
Generating Coverage Histogram...
Generating Unbinned 1-Minute Impulse Actogram Grid...
Generating Unbinned 1-Minute Filled Step Actogram Grid...
Success! QC plots saved to: ./QC_Plots_downsample_rollingMean

```



# Rhythmicity Modelling
We should probably mull around in these results and qc them for a bit. But once we feel good about the filtering method we can take these exact signals and do LS on them to see if they are periodic.

```powershell
python .\run_lomb_scargle.py --csv_in ".\diet_1min_activity.csv" --outdir ".\ls_test"
```

Again, the output for this data will be the specified directory. Read this script to understand a bit more about what we are doing. Specifically, we are running LS on each individuall' locomotor signal and trying to detect periods between 16 and 32 h. We will likely use this test run to inform our final periodicity analysis.


## Mortality Plots
In this directory it felt like a good idea to also generate the final mortality plots. 

We are using the `plot_mortality.ipynb` and providing the appropriate paths to our master parquets in `Rpadi_Video_Tracking_Analysis/H5toParquet/output/final/`. We additionally save the plots to svg in the `Mortality_Plots` directory in our current working directory.


# Final Analysis

The script used for the final video tracking analysis (diet) is `generate_activity_bins_FPSdownsample_rollingMean.py`. This script was run with the following options as shown above.
Its important to note that our data is now in 30 FPS.
i

```powershell
python generate_activity_bins_FPSdownsample_rollingMean.py --input_dir "../H5toParquet/output/final/" --out_file "./diet_1min_activity_downsample_rollingMean.csv" --orig_fps 60 --target_fps 30 --smooth_window 5 --jitter 5.0 --max_jump 50.0 --bout 76.0 --cores 2

# runs in less than 5 minutes with cores = 2. Could probably go up to 4 (32 GB ram on my machine).
```
