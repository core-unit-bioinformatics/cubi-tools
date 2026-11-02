import logging
import pathlib as pl
import shutil
import typing as typ

import tomlkit

import cubitools.commons.utils_func.payloads as ctpl
from cubitools import __debug_run__, __package__, __version__
from cubitools.commons.constants import __STRUCT_INIT_LOG_HANDLER
from cubitools.commons.env import CUBITOOLS_ENVIRONMENT as CT_ENV
from cubitools.commons.utils_cls.git_config import (
    GitConfigAccountOrg,
    GitConfigAccountUser,
    GitConfigPreset,
    GitConfigRemote,
)

if typ.TYPE_CHECKING:
    from cubitools.commons.utils_cls.logging import CubiToolsLogger

# see explanation in commons::constants.py
LOGGER_NAME = f"STRUCTINIT::{__name__}"
LOGGER = logging.getLogger(LOGGER_NAME)
LOGGER.addHandler(__STRUCT_INIT_LOG_HANDLER)
if __debug_run__:
    LOGGER.setLevel(logging.DEBUG)
else:
    LOGGER.setLevel(logging.WARNING)


class CubiToolsConfig:
    __slots__ = [
        "config_file",
        "config",
        "logger",
        "git_remotes",
        "git_accounts",
        "git_presets",
        "templates",
    ]

    def __init__(self, config_file: pl.Path, logger: logging.Logger) -> None:
        self.config_file = config_file
        self.logger: logging.Logger | CubiToolsLogger = logger
        self.logger.debug(f"CT-CONFIG init w/ config file set to: {self.config_file}")
        self.config = self._load_config_file()
        self.git_remotes: dict[str, GitConfigRemote] | None = None
        self.git_accounts: (
            dict[str, GitConfigAccountUser | GitConfigAccountOrg] | None
        ) = None
        self.git_presets: dict[str, GitConfigPreset] | None = None
        self.templates = None
        return None

    def _load_config_file(self) -> tomlkit.TOMLDocument | dict[str, typ.Any]:
        if not self.config_file.is_file():
            warn = (
                "No CUBI-Tools config file detected "
                f"at location: {self.config_file}. "
                "Attempting to deploy default config..."
            )
            self.logger.warning(warn)
            default_config_path = ctpl.get_payload_config_path()
            try:
                self.config_file.parent.mkdir(exist_ok=True, parents=True)
                shutil.copy(default_config_path, self.config_file)
            except (IOError, OSError) as exc:
                err_msg = (
                    f"Could not copy default config to location: {self.config_file} - "
                    f"Error message: {str(exc)} - "
                    "Ignoring and proceeding with empty config."
                )
                self.logger.warning(err_msg)
                return dict()
            else:
                self.logger.debug("Default config deployed successfully")

        with open(self.config_file, "r") as dump:
            cfg = tomlkit.load(dump)
        cfg[__package__] = {"version": f"v{__version__}"}
        self.logger.debug("Config file loaded")
        return cfg

    def _write_config_file(self) -> typ.NoReturn:
        raise NotImplementedError

    def set_logger(self, logger: "CubiToolsLogger") -> None:
        msg = (
            f"Replacing active logger {self.logger.name} with new logger {logger.name}"
        )
        self.logger.debug(msg)
        self.logger = logger
        return None

    def get_plain_config(self) -> tomlkit.TOMLDocument | dict[str, typ.Any]:
        self.logger.debug("Handing out plain config...")
        return self.config

    def set_git_config(
        self,
        git_remotes: dict[str, GitConfigRemote] | None = None,
        git_accounts: dict[str, GitConfigAccountUser | GitConfigAccountOrg]
        | None = None,
        git_presets: dict[str, GitConfigPreset] | None = None,
    ) -> None:
        self.logger.debug("Setting git config")
        if git_remotes is not None:
            self.logger.debug("Updating git remotes")
            self.git_remotes = git_remotes
        if git_accounts is not None:
            self.logger.debug("Updating git accounts")
            self.git_accounts = git_accounts
        if git_presets is not None:
            self.logger.debug("Updating git presets")
            self.git_presets = git_presets
        return None

    def get_git_preset_names(self) -> list[str]:
        """get_git_preset_names is slightly out of place
        here but necessary to make the git preset names
        dynamically available when building the parser
        for the git subcommand.

        Returns:
            _type_: _description_
        """
        if self.git_presets is not None:
            return list(self.git_presets.keys())
        git_presets = []
        try:
            for preset in self.config["git"]["preset"]:
                git_presets.append(preset["name"])
        except KeyError:
            # TODO - unclear what should
            # happen right *here*
            git_presets = ["ERROR_NO_PRESETS"]
        return git_presets


CUBITOOLS_CONFIG = CubiToolsConfig(CT_ENV.cfg_file, LOGGER)
