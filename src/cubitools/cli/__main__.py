#!/usr/bin/env python3

import argparse as argp

from cubitools import __prog__, __usage__, \
    __version__, __cubitools__
import cubitools.cli.subparsers as subcmd
import cubitools.commons.logging as ctlog


def setup_cli_parser():

    parser = argp.ArgumentParser(
        prog=__prog__,
        usage=__usage__,
        epilog=__cubitools__,
        formatter_class=argp.RawTextHelpFormatter,
        exit_on_error=False
    )

    general_args = parser.add_argument_group(title="General parameters")

    general_args.add_argument(
        "--version", "-v",
        action="version",
        version=f"{__prog__} {__version__}",
        help="Print the version and exit."
    )

    general_args.add_argument(
        "--debug", "-d", "-dbg",
        action="store_true",
        default=False,
        dest="debug",
        help="Sets the logging level to DEBUG."
    )

    subparsers = parser.add_subparsers(
        title="::: CUBI-Tools subcommands ::",
        metavar="SUBCMD",
        dest="subcommand"
    )

    subcommands = subcmd.add_module_level_parsers(subparsers)

    subparser_help = (
        "Please select one of the subcommands "
        "and run '--help' to see the command-"
        "specific usage information.\nThe following "
        "subcommands are available:\n\n"
    )

    for cmd_name, cmd_desc in subcommands:
        subparser_help += f"{cmd_name} - {cmd_desc}\n"
    subparser_help += "\n"

    setattr(subparsers, "help", subparser_help)

    return parser


def run_app():

    exit_code = 0

    main_parser = setup_cli_parser()
    try:
        args = main_parser.parse_args()
    except argp.ArgumentError:
        # note that this catches only
        # main parser arg errors, not
        # subparser arg errors
        main_parser.print_help()
        raise

    run_logger_name = "run"
    if args.subcommand is None:
        pass
    else:
        run_logger_name += f"-{args.subcommand}"

    run_logger = ctlog.get_run_logger(run_logger_name, args.debug)
    run_logger.debug(f"Logger name: {run_logger_name}")

    try:
        # this relies on
        # 'parser.set_defaults(exec=<main-module-exec-function>)'
        # in the respective sub-modules
        main_parser.exec(args, run_logger)
    except AttributeError:
        # this means no subcommand was selected, print help/usage
        main_parser.print_help()
        exit_code = 2

    return exit_code


if __name__ == "__main__":
    run_app()
