# CUBI tools

This repository is a collection of helper tools and useful scipts for internal and
external use. The CUBI Tools are implemented with minimal dependencies outside of the
Python standard library (Python v3.11). Currently, the only non-standard packages are
`toml` and `semver`, which must be available to execute any CUBI tool.

# Installation

The CUBI Tools do not work as standalone Python scripts. Please follow the below
instructions to install the CUBI Tools inside a dedicated Conda environment.

## For (CUBI) developers

0. Clone the repository and change into the repository root directory.
1. Create the Conda environment specified in `envs/conda/cubi-tools-dev.yaml`:
    - `conda env create -f envs/conda/cubi-tools-dev.yaml`
2. Activate the environment:
    - `conda activate cubi-tools-dev`
3. Install the CUBI tools:
    - `pip install --editable .`

## For users

0. Clone the repository and change into the repository root directory.
1. Create the Conda environment specified in `envs/conda/cubi-tools.yaml`:
    - `conda env create -f envs/conda/cubi-tools.yaml`
2. Activate the environment:
    - `conda activate cubi-tools`
3. Install the CUBI tools:
    - `pip install .`

# CLI tools available after installation

For details, please refer to the command line help of each tool (`--help`).

- `cubitools arch`: create tar archives for cold data, with optional size limiting and file manifest creation -> [cubitools arch docs](docs/tools/arch.md)
- `cubitools git`: automate initializing, cloning and normalizing git repositories -> [cubitools git docs](docs/tools/git.md)
- `ct-upd-md`: creates or updates metadata files in a CUBI repository -> [ct-upd-md docs](docs/tools/update_metadata.md)
- `ct-upd-wf`: creates or updates the CUBI (Snakemake) workflow template in a CUBI repository -> [ct-upd-wf docs](docs/tools/update_workflow.md)
- `ct-hpc`: collect infos about the cluster/machine configuration (ONLY WORKS WITH PBS Pro) -> [ct-hpc docs](docs/tools/cluster_info.md)

# Usage examples

## Initializing a new Snakemake workflow repository

This example specifies the metadata and workflow template versions
explicitly (latest versions at the time of writing).

```
$ cubitools git --init workflow-smk-foobar --init-preset qb-all
$ ct-upd-md --target-dir workflow-smk-foobar/ --git-branch v1.8.0
$ ct-upd-wf --workflow-target workflow-smk-foobar/ --branch v1.6.0
```

# Citation

If not indicated otherwise above, please follow [these instructions](CITATION.md) to cite this repository in your own work.
