#!/usr/bin/env python3

import argparse as argp
import collections as col
import hashlib
import pathlib as pl
import shutil
import subprocess as sp
import sys
import urllib
import urllib.parse

import semver
import toml

from cubitools import __prog__, __license__, __version__
from cubitools import __cubitools__
from cubitools.constants import DEFAULT_WORKING_DIR, \
    UPD_MD_DEFAULT_TEMPLATE_REPO, \
    UPD_MD_DEFAULT_BRANCH_NAME, \
    UPD_MD_DEFAULT_METADATA_FILES


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

    parser.add_argument(
        "--target-dir", "-t",
        "--update-dir", "-u",
        type=lambda x: pl.Path(x).resolve(strict=True),
        dest="target_dirs",
        nargs="+",
        help=(
            "Path to the CUBI repository where the metadata should be updated. "
            "This repository is the target of the update operation. "
            "Note that you can also specify a space-separated list of "
            "repository paths that will all be updated to the same "
            "metadata version."
        ),
        required=True
    )

    parser.add_argument(
        "--template-metadata-repository",
        "--reference-repository",
        "--metadata-source",
        "--ref-repo", "-r", "-md",
        type=str,
        dest="metadata_source",
        default=UPD_MD_DEFAULT_TEMPLATE_REPO,
        help=(
            "Reference repository used as template for the metadata files. "
            "This repository is the source of the update operation. "
            f"Default: {UPD_MD_DEFAULT_TEMPLATE_REPO}"
        )
    )

    parser.add_argument(
        "--external-target",
        "--forked-target",
        "--external",
        "-e", "-ext", "-fork",
        action="store_true",
        default=False,
        dest="external",
        help=(
            "If set, metadata files are copied into the subfolder 'cubi' "
            "underneath the top-level path of the target repository. Default: False "
            "(Must only be set for external/forked repositories!)"
        )
    )

    parser.add_argument(
        "--git-branch", "--git-tag",
        "-branch", "-tag",
        type=str,
        default="main",
        dest="branch_or_tag",
        help=(
            "Branch or tag of the metadata source to update the files "
            "in the target. Default: main"
        )
    )

    parser.add_argument(
        "--dry-run",
        "--dryrun",
        "-d", "-dry",
        action="store_true",
        default=False,
        dest="dry_run",
        help=(
            "Operate in dry run mode, i.e. just report actions "
            "but do not execute them. Default: False"
        )
    )

    parser.add_argument(
        "--create-new-branch",
        "--new-branch",
        "-c", "-n",
        action="store_true",
        default=False,
        dest="new_branch",
        help=(
            "If set, create a new branch in the target before updating files. "
            f"The new branch will be named '{UPD_MD_DEFAULT_BRANCH_NAME}'. "
            "Default: False"
        )
    )

    parser.add_argument(
        "--report-skipped",
        action="store_true",
        default=False,
        dest="report_skipped",
        help="If set, also report skipped (not updated) files. Default: False"
    )

    parser.add_argument(
        "--offline",
        action="store_true",
        default=False,
        dest="offline",
        help="Work offline and skip operations accordingly. Default: False"
    )

    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(status=2)
    args = parser.parse_args()
    return args


def check_online_resource(uri):

    url_parser = urllib.parse.urlparse
    result = url_parser(uri)
    # No support for http - yes [!?]
    return result.scheme == "https"


def determine_local_metadata_source_path(metadata_source_path, target_parent_dir):

    try:
        local_metadata_path = pl.Path(metadata_source_path).resolve(strict=True)
    except FileNotFoundError:
        # check if the path is an online source / URL
        if not check_online_resource(metadata_source_path):
            err_msg = (
                "\n\nERROR\n\n"
                "You specified a path for the metadata source repository that is "
                "neither a local folder nor seems to be an online resource "
                "(note: an online resource must start with https://).\n"
                "Cannot proceed from here - aborting.\n"
                f"\nInvalid metadata source: {metadata_source_path}\n"
            )
            sys.stderr.write(err_msg)
            raise  # raises again FileNotFoundError

        # now we know that it is an online resource;
        # it may nevertheless exist locally.
        local_metadata_path = target_parent_dir.joinpath(
            pl.Path(metadata_source_path).stem
        ).resolve()

    return local_metadata_path


def determine_target_repo_type(target_dir):
    """Determine type of repository based on
    its name: workflow, project or cubi-tools
    itself are supported at the moment.
    TODO
    - use enums
    - read info from metadata repository
    """

    if target_dir.name.startswith("workflow-"):
        target_type = "workflow"
    elif target_dir.name.startswith("project-"):
        target_type = "project"
    elif target_dir.name == "cubi-tools":
        target_type = "tools"
    elif target_dir.name.startswith("template-"):
        if target_dir.name.endswith("-snakemake"):
            target_type = "workflow/template"
    else:
        raise ValueError(
            f"Cannot determine repository type: {target_dir}"
        )
    return target_type


def md5_checksum(file_path):
    """
    Compute the MD5 checksum for a file.
    Args:
        file_path (pathlib.Path): path to file
    Returns:
        md5_hash: MD5 checksum of metadata file
    """
    with open(file_path, "rb") as some_file:
        content = some_file.read()
        md5_hash = hashlib.md5(content).hexdigest()
    return md5_hash


def file_hash_is_identical(file_a, file_b):
    return md5_checksum(file_a) == md5_checksum(file_b)


def check_file_identity(filename, metadata_path, target_path):

    source_version = metadata_path.joinpath(filename).resolve(strict=True)
    target_version = target_path.joinpath(filename).resolve()

    target_file_exists = target_version.is_file()

    file_is_identical = target_file_exists and file_hash_is_identical(
        source_version, target_version
    )

    if file_is_identical:
        reason = None
    elif target_file_exists:
        reason = "MD5 mismatch"
    else:
        reason = "Non-existent target"

    return file_is_identical, reason


def get_labeled_toml_files(local_metadata_source, target_type):
    """Compile a list of relevant pyproject TOML files.
    At the moment, only one ("type_toml") is not constant
    and specific to the type of the repository (workflow, project etc.)

    This function adresses gh#template-metadata-files#12
    """

    # NB: since an OrderedDict is being used as
    # data structure for the TOML configuration,
    # the file order in this list defines how the individual
    # sections appear in the output. This is important
    # to make any meaningful check of file identity relying
    # on the MD5 checksum
    labeled_tomls = []

    # the metadata TOML
    md_toml = local_metadata_source.joinpath("pyproject.toml").resolve(strict=True)
    labeled_tomls.append((md_toml, "metadata"))

    # the repository type-specific TOML (workflow, project etc.)
    type_toml = local_metadata_source.joinpath(
        "tomls", "cubi", target_type, "pyproject.toml"
    ).resolve(strict=True)
    labeled_tomls.append((type_toml, target_type))

    # special template toml if the target repo is a workflow
    if target_type == "workflow":
        wf_template_toml = local_metadata_source.joinpath(
            "tomls", "cubi","workflow", "template", "pyproject.toml"
        ).resolve(strict=True)
        labeled_tomls.append((wf_template_toml, "workflow/template"))

    # the tool/source code formatter TOML,
    # configuring tools such as black
    fmt_toml = local_metadata_source.joinpath(
        "tomls", "formatting", "pyproject.toml"
    ).resolve(strict=True)
    labeled_tomls.append((fmt_toml, None))

    return labeled_tomls


def is_atomic_type(value):
    atomic_types = [bool, str, int, float]
    is_atomic = any(isinstance(value, at) for at in atomic_types)
    return is_atomic


def update_pyproject_sections(labeled_toml_files, target_content):
    """Update target pyproject content in-place.
    Overwrite values in the metadata section, but only add new
    ones keys in all other sections.
    """
    operations = []
    modifying_ops = 0
    processed_sections = []
    new_pyproject = len(target_content) == 0
    if new_pyproject:
        target_content["cubi"] = col.OrderedDict()
    for toml_file, toml_label in labeled_toml_files:
        source_content = load_toml_file(toml_file)
        if toml_label is None:
            # this is the formatting pyproject toml
            # just plain update operation is fine
            target_content.update(source_content)
            processed_sections.append("tool.*")
            continue
        elif new_pyproject:
            target_content["cubi"][toml_label] = col.OrderedDict()
        elif toml_label == "workflow/template":
            if new_pyproject:
                # this is just a simple entry for the workflow
                # template that cannot be automatically updated
                target_content.update(source_content)
                processed_sections.append("workflow.template")
            else:
                # just skip over it
                continue
        else:
            pass
        section_content = source_content["cubi"][toml_label]
        for key, source_value in section_content.items():
            # for all tomls that are not the formatting toml,
            # only create/update key-value pairs if the value
            # is an atomic type; complex types such as lists
            # or OrderedDicts describe repo type-specific
            # metadata that cannot be updated by this script
            if not is_atomic_type(source_value):
                continue
            try:
                target_value = target_content["cubi"][toml_label][key]
                if target_value == source_value:
                    operations.append(("skip-id", key, target_value, "<identical>"))
                elif toml_label == "metadata":
                    # special case: the value is different and we are in
                    # the pyproject metadata section; here, we can just
                    # replace the old value since it cannot be specific
                    # to the repository we are updating.
                    target_content["cubi"]["metadata"][key] = source_value
                    operations.append(("update", key, target_value, source_value))
                    modifying_ops += 1
                else:
                    operations.append(("skip-ex", key, target_value, source_value))
            except KeyError:
                # 1 - new keys can always be added; they just represent
                # an updated/extension of the respective TOML
                # 2 - this code path is always taken for new/empty
                # pyproject tomls; not very efficient
                operations.append(("new", key, "<missing>", source_value))
                target_content["cubi"][toml_label][key] = source_value
                modifying_ops += 1
        processed_sections.append(f"cubi.{toml_label}")

    joined_labels = "|".join(processed_sections)
    summary_info = f"pyproject.toml\nsections: [{joined_labels}]\nupdate operations:\n"
    for op, key, old, new in operations:
        summary_info += f"{op} {key}: {old} -> {new}\n"

    return modifying_ops, summary_info


def update_pyproject_toml(local_metadata_source, target_dir, target_type, dry_run, report_skipped):

    labeled_tomls = get_labeled_toml_files(local_metadata_source, target_type)

    target_pyproject = target_dir.joinpath("pyproject.toml").resolve()
    if target_pyproject.is_file():
        target_content = load_toml_file(target_pyproject)
    else:
        target_content = col.OrderedDict()

    modifying_ops, summary_info = update_pyproject_sections(labeled_tomls, target_content)

    file_updated = False

    if modifying_ops > 0:
        sys.stdout.write(summary_info)
        file_updated = dump_pyproject_toml(target_pyproject, target_type, target_content, dry_run)
    elif report_skipped:
        sys.stdout.write(summary_info)
    else:
        pass
    return file_updated


def dump_pyproject_toml(target_pyproject, target_type, toml_content, dry_run):

    if target_pyproject.is_file():
        adjective = "updated"
    else:
        adjective = "new"

    file_updated = False

    if dry_run:
        info_msg = (
            "\n=== DRY RUN INFO ===\n"
            f"Writing {adjective} pyproject.toml "
            f"for repository of type '{target_type}'.\n"
            f"{adjective.capitalize()} file location: {target_pyproject}"
        )
        sys.stdout.write(info_msg)
    else:
        question = (
            "\n\n=== Request approval for update ===\n"
            f"Writing {adjective} pyproject.toml "
            f"for repository of type '{target_type}'.\n"
            f"{adjective.capitalize()} file location: {target_pyproject}\n"
            "--> Execute?"
        )
        if get_user_approval(question):
            with open(target_pyproject, "w") as pyproject:
                toml.dump(toml_content, pyproject)
            file_updated = True
    return file_updated


def print_dry_run_info(system_call, work_folder=None):

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


def exec_system_call(call, workfolder=None, fail_on_error=True, return_stdout=False):

    try:
        process_return = sp.run(
            call, cwd=workfolder, check=True,
            stdout=sp.PIPE, stderr=sp.PIPE
        )
    except sp.CalledProcessError:
        if fail_on_error:
            raise
    if return_stdout:
        if process_return.stdout is None:
            value = None
        else:
            value = process_return.stdout.decode("utf-8").strip()
    else:
        value = None
    return value


def git_assert_minimal_version(version="2.23.0"):
    """This script uses the git switch command
    that was introduced in v2.23
    """
    git_cmd = ["git", "--version"]
    out = exec_system_call(git_cmd, return_stdout=True)
    out = out.split()[-1]
    git_version_machine = semver.parse_version_info(out)
    git_version_minimal = semver.parse_version_info(version)
    major_ok = git_version_machine.major >= git_version_minimal.major
    minor_ok = git_version_machine.minor >= git_version_minimal.minor
    if not (major_ok and minor_ok):
        raise RuntimeError(
            f"This CUBI tool requires git version {version}+\n"
            f"Git on your system: {out}"
        )
    return


def git_clone(metadata_source, local_metadata_path, dry_run):

    local_base_path = local_metadata_path.parent
    git_cmd = ["git", "clone", metadata_source]
    if dry_run:
        print_dry_run_info(git_cmd, local_base_path)
    else:
        print(f"Cloning metadata resource {metadata_source} to {local_base_path}")
        exec_system_call(git_cmd, local_base_path)
        assert local_metadata_path.is_dir()
    return


def git_update(local_metadata_path, dry_run):
    git_cmd = ["git", "pull", "--all"]
    if dry_run:
        print_dry_run_info(git_cmd, local_metadata_path)
    else:
        print(f"Updating local metadata resource at: {local_metadata_path}")
        exec_system_call(git_cmd, local_metadata_path)
    return


def git_checkout(local_metadata_path, branch_or_tag, dry_run):

    git_cmd = ["git", "checkout", branch_or_tag]
    if dry_run:
        print_dry_run_info(git_cmd, local_metadata_path)
    else:
        print(f"Checking out branch/tag {branch_or_tag} in metadata resource: {local_metadata_path}")
        exec_system_call(git_cmd, local_metadata_path)
    return


def git_new_branch(local_target_path, dry_run):

    new_branch_name = UPD_MD_DEFAULT_BRANCH_NAME
    git_cmd = ["git", "switch", "-c", new_branch_name]
    if dry_run:
        print_dry_run_info(git_cmd, local_target_path)
    else:
        print(f"Creating new branch '{new_branch_name}' in metadata resource {local_target_path}")
        try:
            exec_system_call(git_cmd, local_target_path)
        except sp.CalledProcessError as perr:
            # could mean that branch already exists
            warn_msg = (
                f"\nWARNING: new branch {new_branch_name} may already "
                f"exist in repository {local_target_path}.\n"
                "Verifying...\n"
            )
            sys.stderr.write(warn_msg)
            check_branch = ["git", "branch", "-a"]

            out = exec_system_call(check_branch, workfolder=local_target_path, return_stdout=True)
            out = out.strip().split()
            branch_exists = False
            for branch in out:
                if new_branch_name in branch:
                    branch_exists = True
                    break
            if not branch_exists:
                sys.stderr.write("\nVerify operation failed...\n")
                raise perr
            else:
                sys.stderr.write(
                    "WARNING: branch already exists\nProceeding with update operation...\n"
                )
    return


def git_reset(local_metadata_path, dry_run, branch="main"):

    git_cmd = ["git", "checkout", branch]
    if dry_run:
        print_dry_run_info(git_cmd, local_metadata_path)
    else:
        print(f"Resetting to branch '{branch}' in metadata resource: {local_metadata_path}")
        exec_system_call(git_cmd, local_metadata_path)
    return


def update_file(file_name, local_metadata_path, target_path, dry_run):

    files_identical, reason = check_file_identity(
        file_name, local_metadata_path, target_path
    )
    file_updated = False
    if not files_identical:
        md_source_file = local_metadata_path.joinpath(file_name)
        cmd = ["cp", md_source_file, target_path]
        if dry_run:
            cmd.insert(0, "[pending user approval]")
            print_dry_run_info(cmd)
        else:
            question = (
                "\n\n=== Request approval for update ===\n"
                f"Update from: {md_source_file}\n"
                f"Update to: {target_path}/\n"
                f"Reason: {reason}\n"
                "--> Execute?"
            )
            if get_user_approval(question):
                exec_system_call(cmd)
                file_updated = True
    return file_updated


def get_user_approval(question, attempt=0):
    """
    Function to evaluate the user response to the Yes or No question refarding updating
    the metadata files.
    """
    attempt += 1
    prompt = f"{question} (y/n): "
    answer = input(prompt).strip().lower()
    pos = ["yes", "y", "yay", "1"]
    neg = ["no", "n", "nay", "0"]
    if attempt == 2:
        print("You have one last chance to answer this yes/no (y/n) question")
    if attempt >= 3:
        raise RuntimeError(
            "You failed 3 times to answer a simple yes/no "
            "(y/n) question --- aborting update..."
        )
    if not (answer in pos or answer in neg):
        print(f"That was a [y]es or [n]o question, but you answered: {answer}")
        return get_user_approval(question, attempt)
    return answer in pos


def load_toml_file(file_path):
    """The OrderedDict as mapping class
    is important to preserve the key order
    when writing the file back to the git
    repo path.
    """
    content = toml.load(file_path, _dict=col.OrderedDict)
    return content


def prepare_local_metadata_resource(metadata_source, target_dir, branch_or_tag, dry_run, offline):

    local_metadata_path = determine_local_metadata_source_path(
        metadata_source, target_dir.parent
    )
    if local_metadata_path.is_dir():
        if not offline:
            git_reset(local_metadata_path, dry_run)
            git_update(local_metadata_path, dry_run)
    else:
        if offline:
            raise RuntimeError(
                "Offline mode set but no local metadata source available."
            )
        git_clone(metadata_source, local_metadata_path, dry_run)

    git_checkout(local_metadata_path, branch_or_tag, dry_run)

    return local_metadata_path


def main():

    args = parse_command_line()
    dry_run = args.dry_run

    git_assert_minimal_version()

    if dry_run:
        print("\n=== INFO: this is a dry run | no changes will be made ===\n")

    target_dirs = args.target_dirs
    assert isinstance(target_dirs, list)
    if len(target_dirs) > 1:
        info_msg = (
            f"Specified {len(target_dirs)} target directories for update operation.\n"
            f"First: {target_dirs[0]}\n"
            f"Last: {target_dirs[-1]}\n"
        )
        print(info_msg)
    else:
        print(f"Target directory for the update operation: {target_dirs[0]}")

    local_metadata_path = prepare_local_metadata_resource(
        args.metadata_source, target_dirs[0],
        args.branch_or_tag, dry_run, args.offline
    )

    for target_dir in target_dirs:
        sys.stdout.write(f"\n\n{'#'*80}\n>>> NEW TARGET DIRECTORY <<<\n{target_dir}\n{'#'*80}\n\n")
        if args.new_branch:
            git_new_branch(target_dir, dry_run)
        if args.external:
            target_copy_path = target_dir.joinpath("cubi")
            if not dry_run:
                target_copy_path.mkdir(parents=True, exist_ok=True)
        else:
            target_copy_path = target_dir
        for md_file in UPD_MD_DEFAULT_METADATA_FILES:
            file_updated = update_file(
                md_file, local_metadata_path, target_copy_path, dry_run
            )
            if dry_run:
                assert not file_updated, f"Unintended update: {target_copy_path}/{md_file}"
            if not dry_run and not file_updated and args.report_skipped:
                print(f"File not updated: {target_copy_path}/{md_file}")

        # for pyproject.toml, there are two options:
        # 1) does not exist - must be created specific for type
        # 2) exists; must only be updated with keys/values of the
        # cubi metadata group
        target_type = determine_target_repo_type(target_dir)
        file_updated = update_pyproject_toml(
            local_metadata_path,
            target_copy_path, target_type,
            dry_run, args.report_skipped)

        if dry_run:
            assert not file_updated, f"Unintended file update: {target_copy_path}/pyproject.toml"

    sys.stdout.write("\n\n" + "-"*100 + "\n")
    sys.stdout.write("Update process complete - resetting metadata source repository to main branch\n")

    # a git update / git pull would fail if the last checked out version was referring
    # to a tag, hence we reset here to main
    git_reset(local_metadata_path, dry_run)

    return 0


if __name__ == "__main__":
    main()
