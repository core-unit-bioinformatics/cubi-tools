# cubi-tool "update workflow" / ct-upd-wf

## Developer info

Legacy/prototype script: `src::cubitools::cli::update_workflow.py`

## Tool purpose

The `ct-upd-wf` tool automates updating the (Snakemake) workflow
template files in a CUBI-style workflow repository. The file identity is
established by computing checksums between source and target
files.

## Brief manual

### Preliminaries

The `ct-upd-wf` tool has no *offline* mode and thus needs an active
internet connection to access the following template repository:

`github.com/core-unit-bioinformatics/template-snakemake.git`

At the moment, this tool only support the Snakemake workflow template.

### Running the update

`ct-upd-wf --target [...]`: update the template files in [TARGET] to the latest release
of the template workflow repository (see above).
