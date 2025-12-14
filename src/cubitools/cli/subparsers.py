
import cubitools.cli.git as subcmd_git


def add_module_level_parsers(subparsers):

    added_subcommands = []

    git_name, git_desc = subcmd_git.get_subcommand_parser(subparsers)

    added_subcommands.append((git_name, git_desc))

    return sorted(added_subcommands)
