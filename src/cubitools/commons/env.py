import dataclasses as dcl
import getpass
import os
import pathlib as pl
import socket

import toml

from cubitools.commons.constants import RUNTIME_CONSTANTS


@dcl.dataclass(frozen=True)
class CubiToolsEnv:
    user_home: pl.Path
    user_name: str
    host_name: str
    cache_dir: pl.Path
    state_dir: pl.Path
    config_dir: pl.Path
    env_file: pl.Path
    cfg_file: pl.Path
    log_file: pl.Path


class CubiToolsEnvBuilder:
    """
    """
    def __init__(self):
        self.user_home = pl.Path.home().resolve(strict=True)
        return None

    def build_environment(self):
        os_env = dict(os.environ)
        custom_env, loaded_env = self._check_custom_env(os_env)
        if custom_env is not None:
            loaded_env["env_file"] = custom_env
            ct_env = CubiToolsEnv(**loaded_env)
        else:
            ct_env = dict()
            self._collect_user_info(ct_env)

            fmt = {"USERHOME": self.user_home}
            ct_env["config_dir"] = self._set_env_dir(
                os_env, RUNTIME_CONSTANTS.xdg_config_home,
                RUNTIME_CONSTANTS.config_default.format(**fmt),
            )
            ct_env["state_dir"] = self._set_env_dir(
                os_env, RUNTIME_CONSTANTS.xdg_state_home,
                RUNTIME_CONSTANTS.state_default.format(**fmt),
            )
            ct_env["cache_dir"] = self._set_env_dir(
                os_env, RUNTIME_CONSTANTS.xdg_cache_home,
                RUNTIME_CONSTANTS.cache_default.format(**fmt),
            )
            ct_env["env_file"] = ct_env["state_dir"].joinpath(
                RUNTIME_CONSTANTS.env_file_name
            )
            ct_env["cfg_file"] = ct_env["config_dir"].joinpath(
                RUNTIME_CONSTANTS.cfg_file_name
            )
            ct_env["log_file"] = ct_env["state_dir"].joinpath(
                RUNTIME_CONSTANTS.log_file_name
            )
            ct_env = CubiToolsEnv(**ct_env)
        self._dump_env_file(ct_env)
        return ct_env

    def _check_custom_env(self, os_env):
        try:
            custom_env = pl.Path(
                os_env[RUNTIME_CONSTANTS.cubi_tools_env]
            ).resolve(strict=True)
        except (KeyError, FileNotFoundError):
            custom_env = None
            loaded_env = dict()
        else:
            with open(custom_env, "r") as cfg_dump:
                plain_values = toml.load(cfg_dump)
            loaded_env = dict()
            for key, value in plain_values.items():
                if key.endswith("_dir") or key in ["user_home"]:
                    loaded_env[key] = pl.Path(value).resolve(strict=True)
                elif key.endswith("_file"):
                    loaded_env[key] = pl.Path(value).resolve()
                else:
                    loaded_env[key] = value
        return custom_env, loaded_env

    def _dump_env_file(self, ct_env):

        simple_env = dict(
            (k, str(v)) for k, v in dcl.asdict(ct_env).items()
        )
        with open(ct_env.env_file, "w") as env_dump:
            toml.dump(simple_env, env_dump)
        return

    def _collect_user_info(self, ct_env):
        ct_env["user_name"] = getpass.getuser()
        ct_env["user_home"] = self.user_home
        ct_env["host_name"] = socket.gethostname()
        return

    def _set_env_dir(self, os_env, env_key, dir_default):
        try:
            system_dir = pl.Path(os_env[env_key])
        except KeyError:
            system_dir = None
        if system_dir is not None and system_dir.is_dir():
            ct_env_dir = system_dir.joinpath(RUNTIME_CONSTANTS.ct_subdir)
        else:
            ct_env_dir = pl.Path(dir_default).joinpath(RUNTIME_CONSTANTS.ct_subdir)
        ct_env_dir.mkdir(exist_ok=True, parents=True)
        return ct_env_dir
