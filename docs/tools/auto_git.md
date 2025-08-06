# cubi-tool "git" / ct-git

## Developer info

Legacy/prototype script: `src::cubitools::cli::auto_git.py`

## Tool purpose

The `ct-git` tool automates interacting with CUBI-style git repositories.
The tool enables users and developers to initialize new repositories, to
clone repos from a remote server and to normalize the repository info if
needed.

Relevant SOPs in the the [CUBI knowledge base](https://github.com/core-unit-bioinformatics/knowledge-base/wiki)
are:

- the general [git development process](https://github.com/core-unit-bioinformatics/knowledge-base/wiki/Dev-process)
- the use of [multiple push targets](https://github.com/core-unit-bioinformatics/knowledge-base/wiki/Git-push-targets)

## Brief manual

### Preliminaries

The `ct-git` command uses user identity information stored on the local machine
in so-called *identity files*. If non-existant, these will be created by the tool
via interactively queriying the user - see [the identity files docs](../general/git_identity_files.md)

### subcommand init

`ct-git --init [...]`: initialize a new git repository following the above SOPs.

If you DO NOT run this command on your laptop (your development machine), think
twice if this is really the operation you want to perform. Typically, you run
`ct-git --init [...]` at the start of a new project or when implementing a new
workflow.

### subcommand clone

`ct-git --clone`: clone a repository from a remote server

This command clones the remote git repository and performs the normalization
following the above SOPs if applicable (e.g., setting a secondary push target).

### subcommand norm

`ct-git --norm`: normalize a local repository to CUBI standards

This command is typically executed if you cloned a remote repository manually
(i.e., without using `ct-git --clone`) and need to configure it following
the above SOPs.

