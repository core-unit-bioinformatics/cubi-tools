import collections
import dataclasses as dcl
import logging
import pathlib
import sys
import typing

from cubitools import __debug_run__

@dcl.dataclass(frozen=True)
class CubiToolsConstants:
    timestamp_format: str = "%Y%m%dT%H%M%S"
    log_fmt_stderr: str = "{asctime}.{name}.{levelname}: {message}"
    log_fmt_stdout: str = "{asctime}.{name}.{levelname}: {message}"
    log_fmt_file: str = "{asctime}\t{name}\t{levelname}\t{message}"
    log_fmt_style: typing.Literal["{", "%", "$"] = "{"
    default_text_encoding: str = "utf-8"
    basic_text_encoding: str = "ascii"
    log_file_name: str = "ct-run.log"
    env_file_name: str = "ct-env.toml"
    cfg_file_name: str = "ct-cfg.toml"
    ct_subdir: str = "cubitools"
    # following: some important env keys
    # plus default values as recommended in
    # specifications.freedesktop.org/basedir/latest
    xdg_data_home: str = "XDG_DATA_HOME"
    data_default: str = "{USERHOME}/.local/share"
    xdg_config_home: str = "XDG_CONFIG_HOME"
    config_default: str = "{USERHOME}/.config"
    xdg_state_home: str = "XDG_STATE_HOME"
    state_default: str = "{USERHOME}/.local/state"
    xdg_cache_home: str = "XDG_CACHE_HOME"
    cache_default: str = "{USERHOME}/.cache"
    cubi_tools_env: str = "CUBI_TOOLS_ENV"


CUBITOOLS_CONSTANTS = CubiToolsConstants()


# this here is used to have a logger with
# decent formatting available during the
# setup of the env and config objects.
# Relying on the cubitools::commons::logging
# module would create circular imports
# - this must not be used in any other contexts
__STRUCT_INIT_LOG_FMT = logging.Formatter(
    fmt=CUBITOOLS_CONSTANTS.log_fmt_stderr,
    datefmt=CUBITOOLS_CONSTANTS.timestamp_format,
    style=CUBITOOLS_CONSTANTS.log_fmt_style
)
__STRUCT_INIT_LOG_HANDLER = logging.StreamHandler(stream=sys.stderr)
if __debug_run__:
    __STRUCT_INIT_LOG_HANDLER.setLevel(logging.DEBUG)
else:
    __STRUCT_INIT_LOG_HANDLER.setLevel(logging.WARNING)
__STRUCT_INIT_LOG_HANDLER.setFormatter(__STRUCT_INIT_LOG_FMT)
