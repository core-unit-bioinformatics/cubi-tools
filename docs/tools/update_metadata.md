# cubi-tool "update metadata" / ct-upd-md

## Developer info

Legacy/prototype script: `src::cubitools::cli::update_metadata.py`

## Tool purpose

The `ct-upd-md` tool automates updating the mandatory metadata
information in a CUBI-style repository. The file identity is
established by computing checksums between source and target
files.

## Brief manual

### Preliminaries

The `ct-upd-md` tool has an *offline* mode to update repositories w/o internet access.
However, this nevertheless requires a clone / updated checkout of the template metadata
repository on the local machine:

Run this before disconnecting from the internet:

`ct-git --clone git@github.com:core-unit-bioinformatics/template-metadata-files.git`

### Running the update

`ct-upd-md --target [...]`: update the metadata files in <TARGET> to the latest release
of the metadata files repository (see above)
