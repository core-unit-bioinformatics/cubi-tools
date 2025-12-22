import importlib.metadata as impmd
import logging
import os
import pathlib as pl
import sys

try:
    __version__ = impmd.version("cubitools")
    __pkg_metadata__ = impmd.metadata("cubitools")
    __license__ = __pkg_metadata__["License-Expression"]
    __prog__ = pl.Path(sys.argv[0]).name
    __usage__ = f"{__prog__} [general parameters] [subcommand] [subcommand parameters] --- "
    __cubitools__ = f"{__prog__} v{__version__} ({__license__} license)"
except impmd.PackageNotFoundError:
    # package is not installed
    raise


try:
    __debug_run__ = dict(os.environ)["CT_DEV_DEBUG"] == "1"
except KeyError:
    __debug_run__ = False


