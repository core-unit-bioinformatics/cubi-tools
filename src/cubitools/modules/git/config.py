
from cubitools.commons.config import CUBITOOLS_CONFIG as CT_CONFIG
import cubitools.commons.logging as ctlog
import cubitools.modules.git.structs as gitstructs


LOGGER_NAME = __name__
LOGGER = ctlog.CubiToolsLogger(LOGGER_NAME)


def build_git_config():
    """build_git_config _summary_
    """
    plain_config = CT_CONFIG.get_plain_config()
    try:
        git_remotes_spec = plain_config["git"]["remote"]
        git_remotes = build_git_remotes(git_remotes_spec)
    except KeyError:
        # TODO - query user
        raise
    try:
        git_accounts_spec = plain_config["git"]["account"]
        git_accounts = build_git_accounts(git_accounts_spec, git_remotes)
    except KeyError:
        # TODO - query user
        raise
    try:
        git_presets_spec = plain_config["git"]["preset"]
        git_presets = build_git_presets(git_presets_spec, git_remotes, git_accounts)
    except KeyError:
        # TODO - query user
        raise
    CT_CONFIG.set_git_config(git_remotes, git_accounts, git_presets)
    return None


def build_git_remotes(git_remotes_spec):
    """build_git_remotes _summary_
    """
    git_remotes = dict()
    for remote in git_remotes_spec:
        assert remote["name"] not in git_remotes, \
            f"Duplicate git remote name: {remote['name']}"
        remote_struct = gitstructs.GitConfigRemote(**remote)
        git_remotes[remote_struct.name] = remote_struct
    return git_remotes


def build_git_accounts(git_accounts_spec, git_remotes):
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
            acc_struct = gitstructs.GitConfigAccountUser(**acc_struct)
        elif account["category"] == "org":
            acc_struct = gitstructs.GitConfigAccountOrg(**acc_struct)
        else:
            raise ValueError
        assert acc_struct.handle not in git_accounts, \
            f"Duplicate git handle: {acc_struct.handle}"
        git_accounts[acc_struct.handle] = acc_struct

    return git_accounts


def build_git_presets(git_presets_spec, git_remotes, git_accounts):
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
        if not isinstance(local_user, gitstructs.GitConfigAccountUser):
            err_msg = (
                f"In git preset {preset['name']}, the local user is "
                f"not a regular user account: {preset['local_user']}. "
                "Group/organization accounts cannot be set as local user."
            )
            raise ValueError(err_msg)

        preset_struct = gitstructs.GitConfigPreset(
            **{
                "name": preset["name"],
                "remotes": set_remotes,
                "remote_handles": set_remote_handles,
                "local_user": local_user
            }
        )
        git_presets[preset_struct.name] = preset_struct

    return git_presets
