#!/usr/bin/env python3

import argparse as argp
import logging

from cubitools import __prog__, __usage__, \
    __version__, __cubitools__
import cubitools.cli.subparsers as subcmd
import cubitools.commons.logging as ctlog


LOGGER_NAME = "main"


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
        "--dry-run", "-d", "-dry",
        action="store_true",
        default=False,
        dest="dry_run",
        help="Explain actions but do not execute them."
    )

    general_args.add_argument(
        "--version", "-v",
        action="version",
        version=f"{__prog__} {__version__}",
        help="Print the version and exit."
    )

    general_args.add_argument(
        "--debug", "-dbg",
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

    main_parser = setup_cli_parser()
    try:
        args = main_parser.parse_args()
    except argp.ArgumentError:
        # note that this catches only
        # main parser arg errors, not
        # subparser arg errors
        main_parser.print_help()
        raise

    logger = ctlog.CubiToolsLogger("main", args.debug)
    logger.debug("Logger setup complete - deferring to subcommand")

    try:
        args.exec(args)
    except Exception as err:
        logger.critical()
        raise err

    logger.debug("Back in main - exiting...")
    logging.shutdown()

    return 0


if __name__ == "__main__":
    run_app()
