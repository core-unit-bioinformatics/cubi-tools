import collections
import pathlib


DEFAULT_WORKING_DIR = pathlib.Path(".").resolve(strict=True)


# ===============
# for tool ct-git
GitRemote = collections.namedtuple(
    "GitRemote", ["name", "org", "priority", "url"]
)

# TODO
# Turn this into a full class
# with each instance representing
# a git repository
KNOWN_GIT_REMOTES = {
    "github.com": GitRemote("github", "core-unit-bioinformatics", 1, "github.com"),
    "git.hhu.de": GitRemote("githhu", "cubi", 0, "git.hhu.de"),
}

# this is sorted by priority
DEFAULT_CUBITOOLS_CONFIG_DIR = [
    pathlib.Path.home().joinpath(".config/cubi-tools"),
    pathlib.Path.home().joinpath(".cubi-tools")
]

# ==================
# for tool ct-upd-md
# update metadata
UPD_MD_DEFAULT_BRANCH_NAME = "feat-update-metadata"
UPD_MD_DEFAULT_TEMPLATE_REPO = "https://github.com/core-unit-bioinformatics/template-metadata-files.git"
UPD_MD_DEFAULT_METADATA_FILES = [
    ".gitignore",
    "CITATION.md",
    "LICENSE",
    ".editorconfig"
]