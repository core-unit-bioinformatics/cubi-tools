# CUBI Tool "git" / cubitools git

## Developer info

The `git` subcommand has already been refactored to support the `cubitools` library, i.e.
the shared codebase for all CUBI Tools. Running the refactored version requires configuring
git remotes and presets via the CUBI Tools TOML configuration file that should - by default -
be placed under `$HOME/.config/cubi-tools/ct-cfg.toml`.

### CUBI Tools TOML configuration file

The default location of the main configuration file is `$HOME/.config/cubi-tools/ct-cfg.toml`.

Currently, this config file supports the following git configuration:

```
[git]

# context: specifying the list of git presets
#
# in the following, the default "CUBI" (= qb)
# presets for github, gitlab and the virtual 'all' target

[[git.preset]]
name = "qb-github"
remotes = ["github"]
# the following: the github remote handle,
# which, for the Core Unit, is the organization
remote_handles = ["core-unit-bioinformatics"]
local_user = "YOUR-GITHUB-USER-HANDLE"

[[git.preset]]
name = "qb-githhu"
remotes = ["githhu"]
# the following: the HHU/gitlab remote handle,
# which, for the Core Unit, is the organization
remote_handles = ["cubi"]
local_user = "YOUR-HHU-GITLAB-USER-HANDLE"

[[git.preset]]
name = "qb-all"
remotes = ["github", "githhu"]
remote_handles = ["core-unit-bioinformatics", "cubi"]
local_user = "YOUR-GITHUB-USER-HANDLE"


# context: specifying the list of known git remotes
#
# the priority is relevant for presets that involve
# more than one git remote (see above, 'qb-all' preset)

[[git.remote]]
server = "github.com"
name = "github"
priority = 1

[[git.remote]]
server = "git.hhu.de"
name = "githhu"
priority = 0


# context: specifying the list of git users/accounts
#
# this is required to set the git user name and email
# for each repository according to the relevant preset

[[git.account]]
category = "user"
handle = "YOUR-HHU-GITLAB-USER-HANDLE"
name = "YOUR-FIRSTNAME-LASTNAME"
email = "YOUR-USER-EMAIL"
remotes = ["githhu"]

[[git.account]]
category = "user"
handle = "YOUR-GITHUB-USER-HANDLE"
name = "YOUR-FIRSTNAME-LASTNAME"
email = "YOUR-USER-EMAIL"
remotes = ["github"]

[[git.account]]
category = "org"
handle = "cubi"
remotes = ["githhu"]

[[git.account]]
category = "org"
handle = "core-unit-bioinformatics"
remotes = ["github"]
```

The above configuration is currently *required a priori* for the `cubtitools git` subcommand, i.e.
the user won't be queried for this information at runtime.

## Tool purpose

The `cubitools git` sub-command automates interacting with CUBI-style git repositories.
The tool enables users and developers to initialize new repositories, to
clone repos from a remote server and to normalize the repository info if
needed.

Relevant SOPs in the the [CUBI knowledge base (KB)](https://github.com/core-unit-bioinformatics/knowledge-base/wiki)
are:

- the general [git development process](https://github.com/core-unit-bioinformatics/knowledge-base/wiki/Dev-process)
- the use of [multiple push targets](https://github.com/core-unit-bioinformatics/knowledge-base/wiki/Git-push-targets)

## Brief manual

### Preliminaries

The `cubitools git` subcommand relies on the CUBI Tools TOML configuration file (see above)
to configure git user accounts and remotes. Without that configuration file, this subcommand
will not work.

### git operation 'init'

`cubitools git --init [...]`: initialize a new git repository following the KB SOPs.

If you DO NOT run this command on your laptop (your development machine), think
twice if this is really the operation you want to perform. Typically, you run
`cubitools git --init [...]` at the start of a new project or when implementing a new
workflow.

### git operation 'clone'

`cubitools git --clone [...]`: clone a repository from a remote server

This command clones the remote git repository and performs the normalization
following the KB SOPs if applicable (e.g., setting a secondary push target).

**Important**: The refactored version of the `git` subcommand always operates from
the current working directory. That is, if you execute

```
cubitools git --clone git@github.com:core-unit-bioinformatics/template-metadata-files.git
```

then this will clone the repository `template-metadata-files` into the current
working directory. Older versions of the CUBI Tools `git` command supported a
parameter `--working-directory` to set the target (parent) directory. This is
no longer supported.

### git operation 'norm'

`cubitools git --norm [...]`: normalize a local repository to CUBI standards

This command is typically executed if you cloned a remote repository manually
(i.e., without using `cubitools git --clone`) and need to configure it following
the KB SOPs.

