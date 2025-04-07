import importlib.metadata as impmd
import pathlib as pl
import sys

try:
    __version__ = impmd.version("cubitools")
    __pkg_metadata__ = impmd.metadata("cubitools")
    __license__ = __pkg_metadata__["License-Expression"]
    __prog__ = pl.Path(sys.argv[0]).name
    __cubitools__ = f"CUBI tool '{__prog__}' v{__version__} ({__license__} license)"
except impmd.PackageNotFoundError:
    # package is not installed
    raise