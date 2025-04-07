# CUBI tools

This repository is a collection of helper tools and useful scipts for internal and
external use. The CUBI tools are implemented with minimal dependencies outside of the
Python standard library (Python v3.11). Currently, the only non-standard packages are
`toml` and `semver`, which must be available to execute any CUBI tool.

## Installation

### For developers

0. Clone the repository and change into the repository root directory.
1. Create the Conda environment specified in `envs/conda/cubi-tools-dev.yaml`:
    - `conda env create -f envs/conda/cubi-tools-dev.yaml`
2. Activate the environment:
    - `conda activate cubi-tools-dev`
3. Install the CUBI tools:
    - `pip install --editable .`

### For users

0. Clone the repository and change into the repository root directory.
1. Create the Conda environment specified in `envs/conda/cubi-tools.yaml`:
    - `conda env create -f envs/conda/cubi-tools.yaml`
2. Activate the environment:
    - `conda activate cubi-tools`
3. Install the CUBI tools:
    - `pip install .`

# Available tools

- `ct-git`: automate init, clone and normalization of git repositories. See below for details.
    - legacy script: `src::cubitools::cli::auto_git.py`
- `update_metadata.py`: updates metadata files or initialized a new repo with metadata files
- `update_workflow.py`: updates templated workflow files


# Tool documentation

## ct-git

### Purpose

Automates configuring git repositories on your machine according
to CUBI standards (see [CUBI knowledge base](https://github.com/core-unit-bioinformatics/knowledge-base/wiki)).

### Requirements: identity file(s)

Configuring a git repository requires setting a user name and email address before commits to the repo can be made.
The `ct-git` utility extracts that info from local files. Those files are referred to as "identity files".
By default, these identity files are expected to be located in `$HOME/.config/cubi-tools` and there must be one such file
for each remote that is to be configured; that is, commonly, two files should be there: `github.id` and `githhu.id`.
If these files are not found, the `ct-git` utility is querying the user for that information and creates
the files for all standard CUBI git remotes.

Identity files are simple text files with two lines: line one specifies the user name and line
two specifies the email address:

```
your-name
your-email
```

That information is then used to perform the following operation:

```bash
git config user.name <USERNAME>
git config user.email <EMAIL>
```

## update-metadata.py

Whenever you create a new repository you can use `update-metadata.py` to either populate your repository with
metadata files from scratch or update current metadata files. The script does so by identifying outdated files based on SHA checksums relative to the source repository [template-metadata-files](https://github.com/core-unit-bioinformatics/template-metadata-files).

## update-workflow.py

Whenever you want to update a Snakemake workflow with the latest version of the "template-snakemake" repository, you can use `update-workflow.py`.
The script updates all Snakemake template workflow files except for `/workflow/rules/00_modules.smk` and `/workflow/rules/99_aggregate.smk`,
which are assumed to contain workflow-specific modifications, i.e. module includes and result file aggregations. The script updates the template
workflow files by checking for SHA checksum differences relative to the source repository [template-snakemake](https://github.com/core-unit-bioinformatics/template-snakemake).


# Citation

If not indicated otherwise above, please follow [these instructions](CITATION.md) to cite this repository in your own work.
