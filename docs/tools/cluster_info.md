# cubi-tool "cluster info" / ct-hpc

## Developer info

Legacy/prototype script: `src::cubitools::cli::cluster_info.py`

## Tool purpose

The `ct-hpc` tool collects summary information on HPC infrastructures
such as available queues and servers including their available resources.

**Important**: the current implementation only supports HPCs with a PBS Pro batch system.

## Brief manual

### Preliminaries

For convenience and portability, the current implementation requires *only* the Python3
standard library and the above mentioned prototype script can be executed as is on
an HPC with PBS Pro.

### Running the update

`ct-hpc [...]`: gather information about the current HPC environment
