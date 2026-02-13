
import pathlib as pl

from cubitools.commons.utils_cls.syscall import SysCallInterface


class GitRepository:

    def __init__(self, local_repo_path: pl.Path, git_preset, dry_run: bool, logger=None):
        self.local_path = local_repo_path
        self.repo_name = local_repo_path.name
        if self.local_path.is_dir():
            wd = self.local_path
            self.is_git_repo = wd.joinpath(".git").is_dir()
        else:
            wd = pl.Path(".").resolve(strict=True)
            self.is_git_repo = False

        self.git_exec = SysCallInterface(
            working_dir=wd, executable="git",
            dry_run=dry_run, logger=logger
        )
        self.git_preset = git_preset
        self.logger = logger
        self.user_name = git_preset.local_user.name
        self.user_email = git_preset.local_user.email
        self.active_remotes = None
        return None

    def _build_git_remote_url(self, remote, account):
        """_build_git_remote_url _summary_

        Args:
            remote (_type_): _description_
            remote_handle (_type_): _description_
        """
        srv = remote.server
        hdl = account.handle
        remote_url = f"git@{srv}:{hdl}/{self.repo_name}.git"
        return remote_url

    def _set_user_config(self):
        """_set_user_config _summary_
        """
        if self.logger is not None:
            self.logger.debug(f"Setting git user config: {self.local_path}")
        self.git_exec.run(['config', 'user.name', f'"{self.user_name}"'])
        self.git_exec.run(['config', 'user.email', f'"{self.user_email}"'])
        if not self.git_exec.dry_run:
            assert self.local_path.joinpath(".git").is_dir()
        if self.logger is not None:
            self.logger.debug(f"Setting git user config - done")
        return None

    def _remove_remote(self, remote_name):
        """_remove_remote _summary_

        Args:
            remote_name (_type_): _description_
        """
        if self.logger is not None:
            self.logger.debug(f"Removing remote '{remote_name}' from repo {self.repo_name}")
        self.git_exec.run(["remote", "remove", remote_name])
        return None

    def _parse_remotes(self):
        """_parse_remotes
        """
        # this only reads, hence 'force_exec'
        out, _ = self.git_exec.run(["remote", "-v"], force_exec=True)
        active_remotes = dict()
        for line in out.split("\n"):
            if not line.strip():
                continue
            content = [char for char in line.strip().split() if char != ""]
            assert len(content) == 3, content
            remote_name, remote_url, remote_op = content
            active_remotes[remote_name] = remote_url
        return active_remotes

    def _set_remotes(self):
        """_set_remotes
        """
        if self.logger is not None:
            self.logger.debug(f"Setting remotes for repo: {self.local_path}")

        remotes = self.git_preset.remotes
        remote_accounts = self.git_preset.remote_handles
        high_prio_remote = []
        set_remotes = dict()

        for remote, account in zip(remotes, remote_accounts):
            remote_url = self._build_git_remote_url(remote, account)
            if self.active_remotes is not None:
                try:
                    # see if we can skip
                    active_remote_url = self.active_remotes[remote.name]
                    if active_remote_url == remote_url:
                        if self.logger is not None:
                            self.logger.debug(
                                f"Remote '{remote.name}' already set for repo: {self.repo_name}"
                            )
                        set_remotes[remote.name] = remote_url
                        continue
                    else:
                        self._remove_remote(remote.name)
                except KeyError:
                    # fine - will be removed at the end
                    pass

            self.git_exec.run(["remote", "add", remote.name, remote_url])
            set_remotes[remote.name] = remote_url
            if remote.priority > 0:
                high_prio_remote.append(remote)
                high_prio_remote.append(remote_url)

        if self.active_remotes is not None:
            for active_remote_name in self.active_remotes.keys():
                if active_remote_name not in set_remotes:
                    self._remove_remote(active_remote_name)

        if len(set_remotes) > 1:
            if len(high_prio_remote) != 2:
                n_remotes = len(set_remotes)
                err_msg = (
                    f"Set {n_remotes} remotes for repo {self.local_path}, triggering "
                    "creation of virtual 'all' push target, but more than one "
                    "high priority remote is configured for git preset "
                    f"{self.git_preset.name}: {high_prio_remote}"
                )
                if self.logger is not None:
                    self.logger.error(err_msg)
                raise RuntimeError(err_msg)
            # set virtual all remote, targeting primary remote
            self._set_all_target(high_prio_remote[0], high_prio_remote[1], set_remotes)
        return None

    def _set_all_target(self, prio_remote, prio_remote_url, remote_urls):
        """_set_all_target _summary_

        Args:
            remote (_type_): _description_
            account (_type_): _description_
            remote_url (_type_): _description_
        """
        if self.logger is not None:
            self.logger.debug(f"Setting 'all' target to primary remote: {prio_remote.name}")
        self.git_exec.run(["remote", "add", "all", prio_remote_url])

        for remote_name, remote_url in remote_urls.items():
            if self.logger is not None:
                self.logger.debug(f"Adding remote push target for 'all': {remote_name} / {remote_url}")
            self.git_exec.run(["remote", "set-url", "--add", "--push", "all", remote_url])
        return None

    def init_repo(self):
        """init_repo
        """
        if self.logger is not None:
            self.logger.debug(f"Initializing new repo: {self.local_path}")
        try:
            if not self.git_exec.dry_run:
                self.local_path.mkdir(exist_ok=False, parents=True)
        except FileExistsError as ferr:
            err_msg = (
                "Cannot initialize new git repository for existing path: "
                f"{self.local_path}"
            )
            ferr.add_note(err_msg)
            raise ferr
        self.git_exec.set_wd(self.local_path)
        self.git_exec.run(["init", "--initial-branch=main"])
        self._set_user_config()
        self._set_remotes()
        if not self.git_exec.dry_run:
            self.is_git_repo = True
            self.active_remotes = self._parse_remotes()

        if self.logger is not None:
            self.logger.debug(f"Initializing new repo - done")
        return None

    def norm_repo(self):
        """norm_repo _summary_
        """
        if not self.is_git_repo:
            err_msg = (
                "Cannot normalize git information in path because it is not a "
                f"git repository: {self.local_path}"
            )
            if self.logger is not None:
                self.logger.error(err_msg)
            raise RuntimeError(err_msg)
        self._set_user_config()
        self.active_remotes = self._parse_remotes()
        self._set_remotes()
        self.active_remotes = self._parse_remotes()
        if self.logger is not None:
            self.logger.debug("Normalizing existing repo - done")
        return None
