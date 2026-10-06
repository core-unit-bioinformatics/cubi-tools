import importlib.resources as imprs

from cubitools import __package__
from cubitools.commons.constants import CUBITOOLS_CONSTANTS as CT_CONST


def get_payload_config_path():
    """Get the path to the payload default config
    file that contains a minimal (generic) configuration
    for things such as git remotes and template repos.
    """
    payload_files = imprs.files(__package__)
    default_config = payload_files.joinpath(
        "config", CT_CONST.cfg_file_name
    ).resolve(strict=True)
    return default_config
