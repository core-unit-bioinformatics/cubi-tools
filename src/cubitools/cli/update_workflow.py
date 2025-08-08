#!/usr/bin/env python3

import collections as col
import itertools as itt
import pathlib as pl
import sys
import subprocess as sp
import argparse as argp
import os
import shutil
import hashlib
import urllib

import semver
import toml

from cubitools import __prog__, __license__, __version__
from cubitools import __cubitools__
from cubitools.constants import DEFAULT_WORKING_DIR, \
    UPD_WF_DEFAULT_TEMPLATE_REPO


def parse_command_line():
    """
    Collection of the various options of the 'update-workflow.py' script.
    """
    parser = argp.ArgumentParser(
        prog=__prog__,
        epilog=__cubitools__
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=__version__,
        help="Displays version of this script.",
    )
    parser.add_argument(
        "--workflow-target", "--update-workflow",
        "--workflow",  "-wf",
        type=lambda p: pl.Path(p).resolve(strict=True),
        dest="workflow_target",
        help="Workflow directory that is the target of the update operation.",
        required=True,
    )
    parser.add_argument(
        "--template-workflow-repository",
        "--reference-repository",
        "--workflow-source",
        "--ref-repo", "-r",
        type=str,
        default=UPD_WF_DEFAULT_TEMPLATE_REPO,
        dest="workflow_source",
        help=(
            "Workflow template repository that is the source of the update operation. "
            f"Default: {UPD_WF_DEFAULT_TEMPLATE_REPO}"
        )
    )
    parser.add_argument(
        "--branch",
        "-b",
        type=str,
        default="main",
        help="Branch or version tag from which to update the files. Default: main",
    )
    parser.add_argument(
        "--dry-run",
        "--dryrun",
        "-d",
        "-dry",
        action="store_true",
        default=False,
        dest="dry_run",
        help="Just report actions but do not execute them. Default: False",
    )
    parser.add_argument(
        "--no-git-add", "-noa",
        action="store_true",
        default=False,
        dest="no_git_add",
        help=(
            "If set, do not execute 'git add <updated files>' in the target repository. "
            "This option is ignored in a dry run. Default: False"
        )
    )

    # if no arguments are given, print help
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(2)

    args = parser.parse_args()
    return args


def check_online_resource(uri):

    url_parser = urllib.parse.urlparse
    result = url_parser(uri)
    # No support for http - yes [!?]
    return result.scheme == "https"


def check_is_git_repo(path):
    return path.joinpath(".git").resolve().is_dir()


def check_is_cubi_workflow(path):
    """check_is_cubi_workflow
    This function checks if the target
    dir is based on the CUBI workflow
    template by checking the presence of
    the two indicator files constants
    and modules. Supports both old and
    new workflow templates:
    old - v1.4.0 and older
    new - v1.5.0 and newer

    Args:
        path (_type_): _description_

    Returns:
        bool: true if templated Snakemake workflow
    """
    # check old / v1.4.0 and older
    old_constants_exist = path.joinpath(
        "workflow", "rules", "commons", "10_constants.smk"
    ).is_file()

    # check new
    new_constants_exist = path.joinpath(
        "workflow", "rules", "commons", "10-constants"
    ).is_dir()

    modules_exist = path.joinpath(
        "workflow", "rules", "00_modules.smk"
    ).is_file()

    is_old_template = old_constants_exist and modules_exist
    is_new_template = new_constants_exist and modules_exist

    return is_old_template or is_new_template


def print_dry_run_info(system_call, work_folder=None):
    """TODO: move to library
    """
    if isinstance(system_call, list):
        cmd = " ".join(map(str, system_call))
    else:
        cmd = system_call
    assert isinstance(cmd, str)

    if work_folder is None:
        wd = DEFAULT_WORKING_DIR
    else:
        wd = work_folder

    info_msg = (
        "\n=== DRY RUN INFO ===\n"
        "Would execute command:\n"
        f"> {cmd}\n"
        f"In folder: {wd}\n"
    )
    print(info_msg)

    return


def git_checkout_branch_tag(template_repo, template_branch_tag, is_dry_run, skip_pull=False):
    """
    This function will pull updates from the remote template repository.
    """
    if not skip_pull:
        command_pull = [
            "git",
            "pull",
            "--all",
            "-q",
        ]
        if is_dry_run:
            print_dry_run_info(command_pull, template_repo)
        else:
            _ = sp.run(
                command_pull,
                cwd=template_repo,
                check=True,
            )

    command_checkout = ["git", "checkout", template_branch_tag, "-q"]
    if is_dry_run:
        print_dry_run_info(command_checkout, template_repo)
    else:
        try:
            _ = sp.run(
                command_checkout,
                cwd=template_repo,
                stderr=sp.PIPE,
                stdout=sp.PIPE,
                check=True,
            )
        except sp.CalledProcessError:
            # unclear is special handling is required
            raise
    return None


def git_clone_template(template_remote, wd, is_dry_run=False):
    """
    This function will clone the template repository,
    by default parallel to the workflow target folder.
    """
    command = [
        "git",
        "clone",
        "-q",
        template_remote
    ]
    if is_dry_run:
        print_dry_run_info(command, wd)
    else:
        try:
            _ = sp.run(
                command,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                cwd=wd,
                check=True,
            )
        except sp.CalledProcessError:
            # unclear if special handling is required
            raise
    return None


def calculate_md5_checksum(file_path):
    """
    The MD5 checksum for all files of the local folder or
    for the template-snakemake branch or version tag is determined.

    Args:
        file_path (pathlib.Path): either the path to workflow_target or workflow_branch
        file_to_update (list): files to update

    Returns:
        md5_hash: MD5 checksum of metadata file
    """
    if file_path.is_file():
        with open(file_path, "rb") as metadata_file:
            data = metadata_file.read()
            md5_hash = hashlib.md5(data).hexdigest()
    else:
        md5_hash = ""
    return md5_hash


def update_file(workflow_target, workflow_template, file_to_update, is_dry_run):
    """
    The MD5 checksum of the the local workflow file(s) and the template_snakemake
    file(s) in the desired branch or version tag are being compared.
    If they differ a question to update for each different
    workflow file pops up. If an update is requested it will be performed.
    """
    source_file_path = workflow_template.joinpath(file_to_update).resolve(strict=True)
    target_file_path = workflow_target.joinpath(file_to_update)
    source_md5 = calculate_md5_checksum(source_file_path)
    target_md5 = calculate_md5_checksum(target_file_path)
    if not target_md5:
        target_md5 = "(non-existing)"

    file_updated = True
    if source_md5 != target_md5:
        print('-----')
        print(f"MD5 mismatch for file: {file_to_update}")
        print(f"Target MD5: {target_md5}")
        if is_dry_run:
            print("This is a dry run - no update")
            file_updated = False
        else:
            answer_is_pos = user_response(f"Update '{file_to_update}'")

            if answer_is_pos:
                target_file_path.parent.mkdir(exist_ok=True, parents=True)
                shutil.copyfile(
                    source_file_path, target_file_path
                )
                print(f"'{file_to_update}' was updated!")
            else:
                print(f"User skipped update of '{file_to_update}'")
                file_updated = False
    else:
        print(f"MD5 match for file: {file_to_update}")
        file_updated = False
    return file_updated


def get_workflow_template_version(workflow_repository):
    """
    Read the workflow template version string from a pyproject toml file
    """
    pyproject_file = workflow_repository.joinpath("pyproject.toml").resolve(strict=True)

    pyproject_content = toml.load(pyproject_file, _dict=col.OrderedDict)

    try:
        workflow_template_version = semver.Version.parse(
            pyproject_content["cubi"]["workflow"]["template"]["version"]
        )
    except ValueError:
        raw_version = pyproject_content["cubi"]["workflow"]["template"]["version"]
        if raw_version in ["prototype", "undefined"]:
            workflow_template_version = semver.Version.parse("0.0.0-prototype")
        else:
            raise

    return workflow_template_version, pyproject_content


def update_pyproject_toml(workflow_target, workflow_template, template_remote, updated_files, is_dry_run):
    """Note that a pyproject.toml must exist because the workflow
    repository must have been initialized with the proper metadata first.
    """
    template_version_source, _ = get_workflow_template_version(workflow_template)
    template_version_target, target_pyproject = get_workflow_template_version(workflow_target)

    # first, some sanity check - are we downgrading?
    file_updated = False
    if template_version_source < template_version_target:
        warn_msg = (
            "\n===\nWarning: workflow template version in source (= the reference "
            "repository) is smaller than the workflow template version in "
            "the target. This means you are effectively downgrading the "
            "workflow template in the target repository.\n===\n"
        )
        sys.stderr.write(warn_msg)

    if template_version_source == template_version_target:
        if updated_files:
            err_msg = (
                "Error: workflow template version match between source/reference "
                f"and target repository, but files were updated: {updated_files}. "
                "Please investigate and fix the problem manually. "
                f"Workflow template version: {template_version_target}"
            )
            raise RuntimeError(err_msg)
        else:
            print("Workflow template version is identical - not updating")
    else:
        if is_dry_run:
            print("=== DRY RUN ===")
            print("Not updating workflow template version in pyproject.toml")
            print(f"Would update from version {template_version_source} to version {template_version_target}")
        else:
            version_string = str(template_version_source)
            target_pyproject["cubi"]["workflow"]["template"]["version"] = version_string
            target_pyproject["cubi"]["workflow"]["template"]["pid"] = template_remote

            answer_is_pos = user_response(
                "Ready to update workflow template information "
                "in the target pyproject.toml - proceed"
            )
            if answer_is_pos:
                target_pyproject_file = workflow_target.joinpath("pyproject.toml")
                with open(target_pyproject_file, "w", encoding="utf-8") as pyproject:
                    pyproject.write(
                        toml.dumps(target_pyproject, encoder=None)
                    )
                file_updated = True
            else:
                print("User skipped update of target pyproject.toml")
    return file_updated


def user_response(question, attempt=0):
    """
    Function to evaluate the user response to the Yes or No question regarding updating
    the metadata files.
    """
    attempt += 1
    prompt = f"{question}? (Y/n): "
    answer = input(prompt).strip().lower()
    pos = ["yes", "y", "yay", ""]
    neg = ["no", "n", "nay"]
    if attempt == 2:
        print("YOU HAVE ONE LAST CHANCE TO ANSWER THIS (Y/n) QUESTION!")
    elif attempt >= 3:
        raise RuntimeError(
            "I warned you! You failed 3 times to answer a simple yes/no "
            "question! Please start over!"
        )
    elif not (answer in pos or answer in neg):
        print(f"That was a yes or no question, but you answered: {answer}")
        return user_response(question, attempt)
    else:
        pass

    return answer in pos


def collect_files(root, base_root=None):
    """Collect all files underneath 'root' as
    paths relative to it. If parameter 'base root'
    is given, the relative path is computed relative
    to 'base root'.
    Skips over default CUBI metadata files.
    """
    files = set()
    subdirs = set()
    metadata_files = [
        "pyproject.toml",
        "CITATION.md",
        "LICENSE",
        ".editorconfig",
        ".gitignore"
    ]
    # these two files would commonly
    # be adapted in a workflow and are
    # otherwise empty - just silently skip
    adapted_workflow_files = [
        "00_modules.smk",
        "99_aggregate.smk"
    ]
    for item in root.iterdir():
        if item.name == ".git":
            continue
        if item.name in adapted_workflow_files:
            continue
        if item.is_dir():
            subdirs.add(item)
            continue
        assert item.is_file()
        if base_root is None:
            rel_path = item.relative_to(root)
        else:
            rel_path = item.relative_to(base_root)
        if str(rel_path) in metadata_files:
            continue
        files.add(rel_path)
    if subdirs:
        source_root = root if base_root is None else base_root
        files = files.union(set(
            itt.chain.from_iterable(
                [collect_files(root.joinpath(subdir), source_root) for subdir in subdirs]
            )))
    return sorted(files)


def main():

    args = parse_command_line()
    is_dry_run = args.dry_run

    if is_dry_run:
        print("=== Info: this is a dry run ===")

    print(f"Workflow directory to be updated: {args.workflow_target}\n")

    workflow_template_local = args.workflow_source

    # check if user provided a local path as workflow template repo
    if pl.Path(workflow_template_local).resolve().is_dir():
        workflow_template_local = pl.Path(workflow_template_local).resolve()
        workflow_template_remote = UPD_WF_DEFAULT_TEMPLATE_REPO
        assert check_is_git_repo(workflow_template_local), \
            f"Not a git repo: {workflow_template_local}"

    elif workflow_template_local == UPD_WF_DEFAULT_TEMPLATE_REPO:
        # it's the default...
        workflow_template_remote = UPD_WF_DEFAULT_TEMPLATE_REPO
        workflow_template_local = args.workflow_target.parent.joinpath(
            pl.Path(UPD_WF_DEFAULT_TEMPLATE_REPO).stem
        )
        if check_is_git_repo(workflow_template_local):
            # all good
            pass
        elif workflow_template_local.is_dir():
            raise RuntimeError(f"Path exists, but not a git repo: {workflow_template_local}")
        else:
            git_clone_template(workflow_template_remote, workflow_template_local.parent, is_dry_run)
    elif check_online_resource(workflow_template_local):
        # least likely case: an online resource / remote repository
        # that is not the default - ?
        workflow_template_remote = workflow_template_local
        workflow_template_local = args.workflow_target.parent.joinpath(
            pl.Path(workflow_template_remote).stem
        )
        git_clone_template(workflow_template_remote, workflow_template_local.parent, is_dry_run)
    else:
        # case: WTF
        raise ValueError(
            f"Cannot interpret value for template repository: {workflow_template_local}"
        )

    # at this point: guaranteed that the template repo exists locally;
    # pull/checkout correct branch
    try:
        git_checkout_branch_tag(workflow_template_local, args.branch, is_dry_run)
    except sp.CalledProcessError:
        # maybe the repo is in detached HEAD state
        git_checkout_branch_tag(workflow_template_local, args.branch, is_dry_run, skip_pull=True)

    # check if the target workflow is really based on the CUBI template
    if not check_is_cubi_workflow(args.workflow_target):
        # one exception: entirely new workflow folder
        answer_is_pos = user_response(
            "Workflow folder is either new/uninitilized "
            "or not based on the official CUBI template. "
            "Please confirm - proceed with update"
        )
        if not answer_is_pos:
            raise RuntimeError(f"Cannot update target folder: {args.workflow_target}")

    file_update_candidates = collect_files(workflow_template_local)
    print(f"Identified {len(file_update_candidates)} template files as candidates for updating")

    wf_target = args.workflow_target
    updated_files = []
    skipped_files = []
    for rel_file_path in file_update_candidates:
        file_updated = update_file(
            wf_target, workflow_template_local, rel_file_path, is_dry_run
        )
        if file_updated:
            updated_files.append(rel_file_path)
        else:
            skipped_files.append(rel_file_path)

    file_updated = update_pyproject_toml(
        wf_target, workflow_template_local,
        workflow_template_remote.strip(".git"),
        updated_files, is_dry_run
    )
    if file_updated:
        updated_files.append("pyproject.toml")
    else:
        skipped_files.append("pyproject.toml")


    # For 'git pull' you have to be in a branch of the template-snakemake repo to
    # merge with. If you previously chose a version tag to update from, 'git pull' will
    # throw a waning message. This part will reset the repo to the main branch to avoid
    # any warning message stemming from 'git pull'
    git_checkout_branch_tag(workflow_template_local, "main", is_dry_run, skip_pull=True)

    if is_dry_run:
        print("Dry run completed")
        for file_path in file_update_candidates:
            print(f"File update candidate: {file_path}")
    else:
        print("Update completed")
        print("Updated files:")
        for file_path in updated_files:
            print(f"Updated: {file_path}")

    return None


if __name__ == "__main__":
    main()
