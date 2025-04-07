import collections
import pathlib


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


DEFAULT_WORKING_DIR = pathlib.Path(".").resolve(strict=True)

# this is sorted by priority
DEFAULT_CUBITOOLS_CONFIG_DIR = [
    pathlib.Path.home().joinpath(".config/cubi-tools"),
    pathlib.Path.home().joinpath(".cubi-tools")
]