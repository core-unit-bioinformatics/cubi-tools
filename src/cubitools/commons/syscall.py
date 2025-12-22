
import pathlib as pl
import shutil as sh
import hashlib as hl
import subprocess as sp

import semver

from cubitools.commons.constants import CUBITOOLS_CONSTANTS as CT_CONST
from cubitools.commons.env import CUBITOOLS_ENVIRONMENT as CT_ENV


class SysCallInterface:

    def __init__(self, working_dir=None, executable=None, logger=None):

        self._compute_object_id()
        self.logger = logger
        self.wd = pl.Path(".").resolve(strict=True)
        if working_dir is not None:
            self.set_wd(working_dir)
        self.exec = None
        self.exec_version = "unknown"
        if executable is not None:
            self.set_exec(executable)
        if self.logger is not None:
            self.logger.debug(f"SysCallInterface {self._id} init w/ wd: {self.wd}")
            self.logger.debug(
                f"SyscallInterface {self._id} init w/ exec: {self.exec} "
                f"v{self.exec_version}"
            )
        return None

    def _compute_object_id(self) -> None:

        obj_id = str(id(self)).encode("utf-8")
        self._id = hl.sha1(obj_id).hexdigest()[:6].upper()
        return None

    def _set_exec_version(self) -> None:

        common_options = ["--version", "-v", "-ver", "version"]

        for version_option in common_options:
            try:
                out, _ = self.run([version_option])
            except sp.CalledProcessError:
                # assumption: it's the wrong version
                # string for the executable - ignore
                pass
            else:
                for component in out.split():
                    try:
                        version = semver.parse_version_info(component)
                    except ValueError:
                        # not a valid version string
                        pass
                    else:
                        self.exec_version = str(version)
                        break
                break
        return None

    def _present_dry_run_info(self, command: list[str]) -> None:

        if self.logger is None:
            return None
        cmd_str = " ".join(command)
        self.logger.tell_user(f"=== SysCallInterface {self._id} DRY RUN info ===")
        self.logger.tell_user(f"Current path: {CT_ENV.path}")
        self.logger.tell_user(f"My working directory: {self.wd}")
        self.logger.tell_user(f"Command: {cmd_str}")
        return None

    def run(self, command: list[str], dry_run: bool=False) -> tuple[str, str]:

        if self.exec is not None:
            _short_form = pl.Path(self.exec).name
            if command[0] not in [self.exec, _short_form]:
                command = [self.exec] + command
        out, err = "", ""
        if dry_run:
            self._present_dry_run_info(command)
        else:
            try:
                exit_state = sp.run(
                    command, check=True, shell=False, cwd=self.wd,
                    capture_output=True, encoding=CT_CONST.default_text_encoding
                )
            except sp.CalledProcessError as cperr:
                if self.logger is not None:
                    msg = f"Command failed - exit {cperr.returncode}: {cperr.cmd}"
                    self.logger.error(msg)
                    err_msg = cperr.stderr.strip().split()
                    err_msg = " /// ".join(err_msg)
                    msg = f"Returned stderr: {err_msg}"
                # in this context, it cannot be determined
                # if the error was a probable outcome or not,
                # so handling needs to happen in the calling context
                raise cperr
            else:
                out = exit_state.stdout
                err = exit_state.stderr
                assert isinstance(out, str)
                assert isinstance(err, str)

        return out, err

    def set_wd(self, working_dir: str | pl.Path) -> None:

        wd_path = pl.Path(working_dir).resolve(strict=True)
        if not wd_path.is_dir():
            raise TypeError(
                f"Working directory path is not a directory: {working_dir}"
            )
        self.wd = wd_path
        if self.logger is not None:
            self.logger.debug(f"SysCallInterface {self._id} wd changed to: {self.wd}")
        return None

    def set_exec(self, executable: str) -> None:

        if self.exec is not None:
            err_msg = (
                f"Attempt to reset fixed executable for SysCallInterface {self._id} "
                f"from {self.exec} to {executable} is forbidden - invalid operation."
            )
            raise RuntimeError(err_msg)
        exec_path = sh.which(executable)
        if exec_path is None:
            err_msg = (
                f"Executable {executable} cannot be located "
                f"under current path: {CT_ENV.path}"
            )
            raise RuntimeError(err_msg)
        self.exec = exec_path
        self._set_exec_version()
        if self.logger is not None:
            self.logger.debug(
                f"SysCallInterface {self._id} exec set to: {self.exec} "
                f"v{self.exec_version}"
            )
        return None
