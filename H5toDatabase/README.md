# H5 to Database Source Code

## Environment

In this environment we will use the default uv venv that we have been using in our analysis

Currently, we are working with on the D: drive to save space but will merge into the shared analysis directory after completion of database generation.

Thus, keeping everything relative to this directory is imperative. Our raw data we will provide with a absolute path so that we do not need to keep it inside of our directory. For people using this code in the future, be sure to provide the correct path to the raw data which will be hosted in a separate repository due to size.

## Introduction

This project will entail assigning correct identities to all tracked individuals in H5 sleap files for a given video replicate (1 rep = 96 total videos/h5 files). We intentionally used sleap in inference mode without ID tracking to have better performance/speed and since we know the ROI of each individual.

Additionally, since 1 replicate contains 96 sequential hours of video, we want to do this across all videos. Further, we want to concatenate all the tracking data together into a single database. This database can then be utilized for downstream locomotion and actigraphy analysis.

## Prototyping  

Before deploying a snakemake workflow to do this across all of our samples, we first want to build a prototype in an .ipynb. We will use our uv kernel from the `Rpadi_Video_Tracking_Analysis` venv here. 

Please see the prototyping `prototypeH5toDatabase.ipynb` file for a running ledger of the features of this workflow. Additionally, visualizations and benchmarks can be found in that file.

## Deploying with Snakemake

After we prototyped for a bit, we now have a good idea of how to run this workflow to go from H5 to sorted and concatenated parquet files that can be used in R/python etc. for downstream analysis.

We now want to run this type of an analysis on all of our 16 reps (8 in LD and 8 in DD conditions). Since this is a lot of processing, we want to use snakemake to manage all of this for obvious reasons.

While we will build this snakemake workflow inside of this directory in OneDrive. We will move it onto our C: or D: drive when its time to run. We can still point to our uv venv by activating the env that we currently have in our OneDrive folder. 

Additionally, we can point to all of our data directories with hard coded paths in the config. To re-do this on another machine or directory, just change those paths to where the data lives...

Once we have our code copied over we can first activate our env...

```powershell
# This will activate our uv venv...
# Anyone can recreate this venv based on the pyproject.toml file in our `Rpadi_Video_Tracking_Analysis` directory. Will be pushed to a remote...

# first cd to the dir where we want to work...
cd " C:\Users\nalamlab\Desktop\H5toDatabase"

# activate venv 
. "C:\Users\nalamlab\OneDrive - Colostate\NIFA_PROJECT\Obj2\Rpadi_Video_Tracking_Analysis\.venv\Scripts\activate.ps1"
```

After we have set our uv venv. Everything should be good to go since we already have snakemake installed as a uv tool on our machine. It's available in any directory.

```powershell
# We can see what snakemake wants to run in a dryrun...
snakemake -np
```

We can see the successful output showing:

```md

Shell command: None
Job stats:
job                  count
-----------------  -------
h5_spatial_assign     1536
merge_replicate         16
all                      1
total                 1553

```

Now we can proceed and run this code with 16 cores. It will right intermediate files to disc and then delete them after finishing.

```powershell
# if we give the merge_replicate rule all 16 cores, it will scale to big and run out of ram.
# we need to set a cap of 4 for the merge replicate dataset.
snakemake -c 16 --set-threads merge_replicate=4
```

Once finished we can copy this directory back into OneDrive for git tracking in our master `Rpadi_Video_Tracking_Analysis` directory and also keep it safely backed-up w/ OneDrive.


## AI Usage 
This codebase was developed in part with Gemini Flash Extended 3.6. Any code generation or debugging suggestions were explicitly reviewed, added to the document, updated with either more explicit comments and notes or direct changes to the code, and validated by Daniel Kunk.