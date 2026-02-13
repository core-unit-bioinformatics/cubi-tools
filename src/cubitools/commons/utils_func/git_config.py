"""This module is in principle a candidate
to be turned into a class (GitConfig), but
the functionality is in essence just converting
primitives into datastructures. All the config
information of a CUBI Tools run should be contained
in the CubiToolsConfig object to simply dumping
the current config to a single config file.
"""


from cubitools.commons.config import CUBITOOLS_CONFIG as CT_CONFIG
from cubitools.commons.utils_cls.git_config import GitConfigAccountOrg, \
    GitConfigAccountUser, GitConfigPreset, GitConfigRemote


def build_git_config():
    """This is a convenience function to trigger
    the typed built of the git configuration that
    is loaded by default when the CUBITOOLS config
    object is initialized.
    This functions has only the side-effect of setting
    the git config objects in the CT_CONFIG.
    """
    plain_config = CT_CONFIG.get_plain_config()
    try:
        git_remotes_spec = plain_config["git"]["remote"]
        git_remotes = _build_git_remotes(git_remotes_spec)
    except KeyError:
        # TODO - query user
        raise NotImplementedError("user query missing")
    try:
        git_accounts_spec = plain_config["git"]["account"]
        git_accounts = _build_git_accounts(git_accounts_spec, git_remotes)
    except KeyError:
        # TODO - query user
        raise NotImplementedError("user query missing")
    try:
        git_presets_spec = plain_config["git"]["preset"]
        git_presets = _build_git_presets(git_presets_spec, git_remotes, git_accounts)
    except KeyError:
        # TODO - query user
        raise NotImplementedError("user query missing")

    CT_CONFIG.set_git_config(git_remotes, git_accounts, git_presets)
    return None


def _build_git_remotes(git_remotes_spec):
    """build_git_remotes _summary_
    """
    git_remotes = dict()
    for remote in git_remotes_spec:
        assert remote["name"] not in git_remotes, \
            f"Duplicate git remote name: {remote['name']}"
        remote_struct = GitConfigRemote(**remote)
        git_remotes[remote_struct.name] = remote_struct
    return git_remotes


def _build_git_accounts(git_accounts_spec, git_remotes):
    """build_git_accounts
    Args:
        git_accounts_spec (_type_): _description_
        git_remotes (_type_): _description_
    """
    git_accounts = dict()
    for account in git_accounts_spec:
        set_remotes = []
        for remote in account["remotes"]:
            try:
                git_remote = git_remotes[remote]
            except KeyError:
                # TODO - query user
                raise KeyError
            set_remotes.append(git_remote)
        acc_struct = dict(account)
        acc_struct["remotes"] = set_remotes
        if account["category"] == "user":
            acc_struct = GitConfigAccountUser(**acc_struct)
        elif account["category"] == "org":
            acc_struct = GitConfigAccountOrg(**acc_struct)
        else:
            raise ValueError
        assert acc_struct.handle not in git_accounts, \
            f"Duplicate git handle: {acc_struct.handle}"
        git_accounts[acc_struct.handle] = acc_struct

    return git_accounts


def _build_git_presets(git_presets_spec, git_remotes, git_accounts):
    """build_git_presets

    Args:
        git_presets_spec (_type_): _description_
        git_remotes (_type_): _description_
        git_accounts (_type_): _description_
    """
    git_presets = dict()
    for preset in git_presets_spec:
        remotes = preset["remotes"]
        remote_handles = preset["remote_handles"]
        if len(remotes) != len(remote_handles):
            err_msg = (
                "You need to configure one git handle "
                f"per git remote. Remotes: {remotes} "
                f"/ Handles {remote_handles}"
            )
            raise ValueError(err_msg)
        try:
            set_remotes = [git_remotes[remote] for remote in remotes]
            set_remote_handles = [git_accounts[handle] for handle in remote_handles]
            local_user = git_accounts[preset["local_user"]]
        except KeyError:
            # TODO - query user
            raise
        if not isinstance(local_user, GitConfigAccountUser):
            err_msg = (
                f"In git preset {preset['name']}, the local user is "
                f"not a regular user account: {preset['local_user']}. "
                "Group/organization accounts cannot be set as local user."
            )
            raise ValueError(err_msg)

        preset_struct = GitConfigPreset(
            **{
                "name": preset["name"],
                "remotes": set_remotes,
                "remote_handles": set_remote_handles,
                "local_user": local_user
            }
        )
        git_presets[preset_struct.name] = preset_struct

    return git_presets
