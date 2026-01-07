
import cubitools.cli.git as subcmd_git
import cubitools.cli.arch as subcmd_arch


def add_module_level_parsers(subparsers):

    added_subcommands = []

    git_name, git_desc = subcmd_git.get_subcommand_parser(subparsers)
    added_subcommands.append((git_name, git_desc))

    arch_name, arch_desc = subcmd_arch.get_subcommand_parser(subparsers)
    added_subcommands.append((arch_name, arch_desc))

    return sorted(added_subcommands)
