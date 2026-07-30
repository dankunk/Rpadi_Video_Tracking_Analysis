# *R padi* Video Tracking Analysis

## Introduction

This directory/repo contains the working scripts and tools utilized for video tracking *Rhopalosiphum padi* behaviors over time.

The subdirectories found within this project repository contain notes, analyses, etc. Each should include a README with some information on the analysis, the environment/packages used, etc.

## Package Management

This analysis will utilize `uv` for package management for now. This is a bit faster than conda and seems to fit our purposes a bit better.

For now, the uv environment will be initialized in the root repository directory. If additional environemnts are needed per analysis (i.e. R projects, conflicting version dependencies, etc.) they should be initialized in each subdirectory.

### Installing uv

We can install uv following the astral docs: https://docs.astral.sh/uv/getting-started/installation/

It's a one liner in the powershell cmd line and installs in seconds. Much easier than downloading anaconda/conda.

### Initializing the uv envi

Next we can initialize the uv environment in our working directory. Note that this will 

```powershell
# deactivate conda
conda deactivate
# install python
uv python install 3.13

uv init --python 3.13

# add some packages
uv add opencv-python matplotlib pandas
```

### Using uv in VScode

When utilizing uv in vscode you need to add a kernel. To do this we can:

```powershell
# Add ipykernel as a dev dependency.
uv add --dev ipykernel
```

Its a good idea to restart vs code...

Now we should be able to grab the kernel in the GUI... If not, go to the command palette and select the correct python interpreter that we just installed with uv...


