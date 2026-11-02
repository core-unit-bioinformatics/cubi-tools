import argparse as argp

import cubitools.cli.arch as subcmd_arch
import cubitools.cli.git as subcmd_git


def add_module_level_parsers(
    subparsers: "argp._SubParsersAction[argp.ArgumentParser]",
) -> list[tuple[str, str]]:
    added_subcommands = []

    git_name, git_desc = subcmd_git.get_subcommand_parser(subparsers)
    added_subcommands.append((git_name, git_desc))

    arch_name, arch_desc = subcmd_arch.get_subcommand_parser(subparsers)
    added_subcommands.append((arch_name, arch_desc))

    return sorted(added_subcommands)
