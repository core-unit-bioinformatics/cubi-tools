#!/usr/bin/env python3

import argparse as argp
import collections as col
import pathlib as pl
import subprocess as sp
import sys

from cubitools import __prog__, __license__, __version__
from cubitools import __cubitools__
from cubitools.constants import KNOWN_GIT_REMOTES, DEFAULT_WORKING_DIR, DEFAULT_CUBITOOLS_CONFIG_DIR


def parse_command_line():

    parser = argp.ArgumentParser(
        prog=__prog__,
        epilog=__cubitools__
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=__version__,
        help="Show version and exit.",
    )

    parser.add_argument(
        "--working-dir", "--root", "-wd", "-w",
        type=lambda path: pl.Path(path).resolve(strict=True),
        default=DEFAULT_WORKING_DIR,
        dest="working_dir",
        help=(
            "Default working / root directory of operations. "
            f"Default: {DEFAULT_WORKING_DIR}"
        )
    )

    mutex = parser.add_mutually_exclusive_group(required=True)
    mutex.add_argument(
        "--clone",
        "-c",
        type=str,
        default=None,
        dest="clone",
        help=(
            "Full (remote) git path to clone in the form of: git@<remote>:<user-or-org>/<repo>.git "
            "Example: auto_git.py --clone git@github.com:core-unit-bioinformatics/cubi-tools.git"
        )
    )
    mutex.add_argument(
        "--init",
        "-i",
        type=lambda x: pl.Path(x).resolve(strict=False),
        default=None,
        dest="init",
        help=(
            "Path to the new repository to initialize. "
            "Example: auto_git.py --init PATH-TO-NEW-REPO [must not exist] --init-preset PRESET"
        )
    )
    mutex.add_argument(
        "--norm",
        "-n",
        type=lambda x: pl.Path(x).resolve(strict=True),
        default=None,
        dest="norm",
        help=(
            "Normalize git remotes for existing repositories. "
            "Example: auto_git.py --norm PATH-TO-EXISTING-REPO"
        )
    )
    parser.add_argument(
        "--init-preset",
        "-ip",
        type=str,
        choices=["github", "githhu", "all"],
        default="githhu",
        dest="init_preset",
        help="Preset for git init operation: github / githhu / all [both remotes]",
    )
    parser.add_argument(
        "--dry-run",
        "--dryrun",
        "-dry",
        "-d",
        action="store_true",
        dest="dryrun",
        default=False,
        help="Just print what you would do, but don't do it",
    )

    parser.add_argument(
        "--cubi-tools-config", "--ct-config", "-cfg",
        "--git-identities", "-g",
        type=lambda x: pl.Path(x).resolve(strict=True),
        dest="cubi_config_dir",
        default=DEFAULT_CUBITOOLS_CONFIG_DIR[0],
        help=(
            "Path to CUBI tools configuration folder. "
            "For this tool, this folder contains the "
            "git identity files for all git remotes. "
            "See README for details; in brief, an identity file for a "
            "remote is a 2-line text file stating the "
            "(1) author name and (2) email. "
            f"Default - any of the following:  {DEFAULT_CUBITOOLS_CONFIG_DIR}"
        )
    )

    parser.add_argument(
        "--no-user-config",
        "--no-cfg",
        "-noc",
        action="store_true",
        default=False,
        dest="no_user_config",
        help="Do not configure user name and email for git repository. Default: False",
    )

    parser.add_argument(
        "--no-all-target",
        "--no-all",
        "-noa",
        action="store_true",
        default=False,
        dest="no_all",
        help="Do not configure multiple push targets / do not add virtual 'all' remote. Default: False",
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        default=False,
        dest="quiet",
        help="If set, do not print usage hints at the end."
    )
    args = parser.parse_args()

    if not args.no_user_config:
        cubi_cfg_dir = check_cubi_config_dir(args.cubi_config_dir)
        setattr(args, "cubi_config_dir", cubi_cfg_dir)

    if args.init is not None and args.init_preset == "githhu":
        setattr(args, "no_all", True)

    # change in response to gh#27
    if args.init is not None and args.init_preset == "github":
        if not getattr(args, "no_all"):
            err_msg = (
                "You selected the init preset 'github' with the virtual "
                "'all' remote.\nThis probably does not make sense because "
                "the CUBI development guidelines state that (standard) "
                "repositories have to exist both on github and on gitlab/HHU.\n"
                "If you are sure you are doing the right thing, please "
                "explicitly set the option '--no-all-target' together with "
                "the 'github' preset."
            )
            raise ValueError(err_msg)

    # change in response to gh#27
    if args.init is not None and args.init_preset == "all":
        if getattr(args, "no_all"):
            raise ValueError("Cannot combine init preset 'all' with option '--no-all-target'")
        # under the hood, just reset the init preset to 'github'
        # if the user selected 'all', which is the default behavior.
        setattr(args, "init_preset", "github")

    return args


def check_git_identity_files(config_dir):

    missing_id_files = []
    for git_remote in KNOWN_GIT_REMOTES.values():
        id_file = config_dir.joinpath(f"{git_remote.name}.id")
        try:
            id_file.resolve(strict=True)
        except FileNotFoundError:
            missing_id_files.append(git_remote.name)
    if len(missing_id_files) > 0:
        err_msg = (
            "The following ID files are missing for "
            f"standard CUBI git remote servers: {missing_id_files}"
        )
        sys.stderr.write(f"\n{err_msg}\n")
    return missing_id_files


def dump_git_id_info(remote_name, cubi_config_dir):

    id_file = cubi_config_dir.joinpath(f"{remote_name}.id")

    query_name = f"Please provide your full name for git remote {remote_name}: "
    user_name = input(query_name)
    assert user_name, "User name cannot be empty"
    query_mail = f"Please provide your e-mail for git remote {remote_name}: "
    user_email = input(query_mail)
    assert user_email, "User e-mail cannot be empty"

    with open(id_file, "w") as dump:
        _ = dump.write(user_name + "\n")
        _ = dump.write(user_email + "\n")
    return


def check_cubi_config_dir(user_set_dir):

    cubi_cfg_dir = None
    if not user_set_dir.is_dir():
        for directory in DEFAULT_CUBITOOLS_CONFIG_DIR:
            if directory.is_dir():
                cubi_cfg_dir = directory
                break
        if cubi_cfg_dir is None:
            cubi_cfg_dir = DEFAULT_CUBITOOLS_CONFIG_DIR[0]
            cubi_cfg_dir.mkdir(parents=True)
    else:
        cubi_cfg_dir = user_set_dir

    missing_id_files = check_git_identity_files(cubi_cfg_dir)
    if len(missing_id_files) > 0:
        for git_remote in missing_id_files:
            dump_git_id_info(git_remote, cubi_cfg_dir)

    return cubi_cfg_dir


def parse_git_url(url):
    try:
        prefix, remainder = url.split("@")
    except ValueError:
        assert "@" not in url
        # this means no "@" in URL, i.e. repo was cloned
        # via https --- must be via ssh to be useful for working
        sys.stderr.write(
            (
                f"\nERROR: repository URL does not contain '@': {url}\n"
                "The repository was likely cloned via 'https' and not via ssh.\n"
                "Please clone/checkout the repo via ssh, e.g., by using the CUBI tools "
                "'ct-git --clone' functionality. Aborting ...\n\n"
            )
        )
        raise

    prefix, remainder = url.split("@")
    remainder, suffix = remainder.rsplit(".", 1)
    assert prefix == suffix == "git"
    remote_by_url, remainder = remainder.split(":", 1)
    assert remote_by_url in KNOWN_GIT_REMOTES
    user_or_org, remainder = remainder.split("/", 1)
    repo_name = remainder
    infos = {
        "remote_url": remote_by_url,
        "remote_name": KNOWN_GIT_REMOTES[remote_by_url].name,
        "user": user_or_org,
        "repo_name": repo_name,
        "priority": KNOWN_GIT_REMOTES[remote_by_url].priority,
        "remote_path": url,
    }
    return infos


def build_default_remote_infos(remote_name, repo_name):
    remote_path = None
    for remote_url, remote_specs in KNOWN_GIT_REMOTES.items():
        if remote_specs.name != remote_name:
            continue
        remote_org = remote_specs.org
        remote_path = f"git@{remote_url}:{remote_org}/{repo_name}.git"
    if remote_path is None:
        raise ValueError(f"Cannot find remote infos: {remote_name}")
    git_infos = parse_git_url(remote_path)
    return git_infos


def set_push_targets(git_infos, wd, dry_run):
    all_remote_paths = []
    for remote_url, remote in KNOWN_GIT_REMOTES.items():
        remote_git_path = f"git@{remote_url}:{remote.org}/{git_infos['repo_name']}.git"
        all_remote_paths.append(remote_git_path)
        cmd = " ".join(["git", "remote", "add", f"{remote.name}", remote_git_path])
        if remote_url == git_infos["remote_url"]:
            continue
        execute_command(cmd, wd, dry_run)

    primary_remote = f"git@{git_infos['remote_url']}:"
    primary_remote += f"{git_infos['user']}/"
    primary_remote += f"{git_infos['repo_name']}.git"
    # set all remote
    cmd = " ".join(["git", "remote", "add", "all", primary_remote])
    execute_command(cmd, wd, dry_run)
    for remote_path in all_remote_paths:
        cmd = " ".join(
            ["git", "remote", "set-url", "--add", "--push", "all", remote_path]
        )
        execute_command(cmd, wd, dry_run)
    return


def get_git_id_settings(id_folder, remote_name):
    id_file = id_folder.joinpath(f"{remote_name}.id").resolve(strict=True)
    with open(id_file, "r") as id_content:
        id_name = id_content.readline().strip().strip('"')
        id_email = id_content.readline().strip().strip('"')
    settings = [
        ("user.name", '"' + id_name + '"'),
        ("user.email", '"' + id_email + '"'),
    ]
    return settings


def set_git_identity(git_infos, wd, id_folder, dry_run):
    primary_remote = git_infos["remote_name"]
    settings = get_git_id_settings(id_folder, primary_remote)
    for key, value in settings:
        cmd = " ".join(["git", "config", key, value])
        execute_command(cmd, wd, dry_run)
    return


def execute_command(cmd, wd, dry_run):
    out = ""
    if dry_run:
        msg = f"\nWould execute...\n\tin directory: {wd}\n\tthis command: {cmd}\n"
        sys.stdout.write(msg)
    else:
        try:
            out = sp.check_output(cmd, shell=True, cwd=wd)
            out = out.decode("utf-8").strip()
        except sp.CalledProcessError as perr:
            sys.stderr.write(f"\nError for command: {perr.cmd}\n")
            sys.stderr.write(f"Exit status: {perr.returncode}\n")
            sys.stderr.write(f"Message: {perr.output.decode('utf-8')}\n")
            raise
    return out


def clone_git(args, wd):
    """Clone a repository, add
    all push target (default: yes);
    configure user name and email
    (default: yes)
    """
    git_infos = parse_git_url(args.clone)
    cmd = " ".join(["git", "clone", f"--origin {git_infos['remote_name']}", args.clone])
    _ = execute_command(cmd, wd, args.dryrun)
    repo_wd = wd.joinpath(git_infos["repo_name"])

    return git_infos, repo_wd


def norm_git(args):
    """Normalize remote name,
    add all push target (default: yes);
    configure user name and email
    (default: yes)
    """
    cmd = " ".join(["git", "remote", "-v"])
    # the following only reads info,
    # no need to exec as dry run
    remotes = execute_command(cmd, args.norm, False)
    if not remotes:
        raise ValueError("No git remotes configured")
    set_remotes = []
    for remote in remotes.split("\n"):
        if "push" in remote:
            continue
        current_name, remote_url, _ = remote.strip().split()
        if current_name == "all":
            # seems unlikely, but if configured,
            # leave as is
            print(f"Skipping over 'all': {remote_url}")
            continue
        remote_infos = parse_git_url(remote_url)
        if remote_infos["remote_name"] != current_name:
            cmd = " ".join(
                ["git", "remote", "rename", current_name, remote_infos["remote_name"]]
            )
            _ = execute_command(cmd, args.norm, args.dryrun)
        set_remotes.append((remote_infos["priority"], remote_infos))
    set_remotes = sorted(set_remotes, reverse=True)
    primary_remote = set_remotes[0][1]

    return primary_remote, args.norm


def init_git(args):
    # NB: git fails if dir not empty,
    # so check if it already exists
    # (proxy for non-empty)
    if args.init.is_dir():
        raise ValueError(
            f"Path already exists: {args.init}\nCannot initialize new git repo."
        )
    if args.dryrun:
        cmd = f"mkdir -p {args.init}"
        msg = f"\nWould create directory...\n\tin directory: {args.init.parent}\n\tthis command: {cmd}\n"
        sys.stdout.write(msg)
    else:
        args.init.mkdir(exist_ok=False, parents=True)
    repo_wd = args.init
    cmd = " ".join(["git", "init", "--initial-branch=main"])
    _ = execute_command(cmd, repo_wd, args.dryrun)
    if not args.dryrun:
        assert repo_wd.joinpath(".git").is_dir(), "git init failed"
    repo_name = repo_wd.name
    git_infos = build_default_remote_infos(args.init_preset, repo_name)
    cmd = " ".join(
        ["git", "remote", "add", f"{args.init_preset}", git_infos["remote_path"]]
    )
    _ = execute_command(cmd, repo_wd, args.dryrun)

    return git_infos, repo_wd


def main():
    args = parse_command_line()
    wd = pl.Path(".").resolve()
    if args.clone is not None:
        git_infos, wd = clone_git(args, wd)
    elif args.init is not None:
        git_infos, wd = init_git(args)
    elif args.norm is not None:
        assert args.norm.joinpath(".git").is_dir()
        git_infos, wd = norm_git(args)
    else:
        raise ValueError("No action specified")

    if not args.no_all:
        set_push_targets(git_infos, wd, args.dryrun)
    if not args.no_user_config:
        set_git_identity(git_infos, wd, args.cubi_config_dir, args.dryrun)

    if not args.quiet:
        hints = (
            "\n=====\n"
            "Usage hints:\n"
            "(1) If you just configured a new repo involving the GitHub remote,\n"
            "do not forget to create an empty repo with the same name on github.com\n"
            "to be able to push the new repo.\n"
            "(2) If you just configured a new repo or created a new branch w/o\n"
            "counterpart in the remote(s), remeber to 'push' with the option\n"
            "'-u/--set-upstream' for every new (!) branch:\n"
            "'git push -u REMOTE-NAME BRANCH-NAME'\n"
            "For example:\n"
            "git push -u all main\n"
            "git push -u github dev\n"
            "=====\n"
        )
        print(hints)

    return 0


if __name__ == "__main__":
    main()
