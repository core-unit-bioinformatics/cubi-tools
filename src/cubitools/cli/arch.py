
from cubitools.commons.env import CUBITOOLS_ENVIRONMENT as CT_ENV
from cubitools.commons.config import CUBITOOLS_CONFIG as CT_CONFIG
from cubitools.commons.enums import Compression, PathType
import cubitools.commons.logging as ctlog
from cubitools.commons.io_path import IOPath


LOGGER_NAME = __name__
LOGGER = ctlog.CubiToolsLogger(LOGGER_NAME)


def get_subcommand_parser(subparsers):

    subcmd_name = "arch"
    subcmd_desc = (
        "CUBI-Tools subcommand to produce (compressed) tar archives "
        "of one or more directories. The 'arch' command supports "
        "chunking the resulting archive by size and produces "
        "manifest files for the archive."
    )

    parser = subparsers.add_parser(
        subcmd_name,
        description=subcmd_desc,
    )

    parser.add_argument(
        "--archive-dirs", "-a",
        type=IOPath.input_dir,
        nargs="+",
        dest="archive_dirs",
        help=""
    )

    parser.add_argument(
        "--out-prefix", "-op",
        type=IOPath.output_prefix,
        dest="out_prefix",
        help=""
    )

    parser.add_argument(
        "--compress", "-c",
        type=Compression,
        choices=list(Compression.__members__.keys()),
        default=Compression.GZIP,
        help=f"Select tar compression tool. Default: {Compression.GZIP.name}"
    )

    parser.add_argument(
        "--chunk-limit", "-lim",
        type=str,
        default="4T",
        dest="chunk_limit",
        help=(
            "Limit the size of the resulting tar archive, i.e. "
            "create several chunks not larger than this limit "
            "if necessary. Set to -1 to deactivate. "
            "Default: 4t[erabyte]"
        )
    )

    parser.add_argument(
        "--scratch-dir", "-s",
        type=IOPath.output_dir,
        default=None,
        dest="scratch_dir",
        help=""
    )

    mutex_manifest = parser.add_mutually_exclusive_group(required=False)

    mutex_manifest.add_argument(
        "--no-manifest", "-nom",
        action="store_true",
        default=False,
        dest="no_manifest"
    )

    mutex_manifest.add_argument(
        "--minimal-manifest", "-mnm",
        action="store_true",
        default=False,
        dest="minimal_manifest"
    )

    mutex_select = parser.add_mutually_exclusive_group(required=False)

    mutex_select.add_argument(
        "--exclude", "-excl",
        type=str,
        nargs="*",
        default=[PathType.HIDDEN.name, PathType.SYMBOLIC.name],
        dest="exclude",
        help=(
            "Exclude file paths matching any of these regular expressions "
            "or attributes. This argument is ignore if '--include' is set. "
            "Default: HIDDEN and SYMBOLIC (= skip over hidden files and "
            "folders and symbolic links)."
        )
    )

    mutex_select.add_argument(
        "--include", "-incl",
        type=str,
        nargs="*",
        default=None,
        dest="include",
        help=(
            "Include only file paths matching any of these regular expressions. "
            "Default: None (= include all paths that are NOT excluded)."
        )

    )

    parser.add_argument(
        "--final-cleanup", "-clean",
        action="store_true",
        default=False,
        dest="final_cleanup",
        help="Delete the archived files and folders."
    )

    parser.set_defaults(exec=exec_arch_module)

    return subcmd_name, subcmd_desc


def exec_arch_module(args):

    LOGGER.set_debug_logging(args.debug)
    CT_CONFIG.set_logger(LOGGER)



    return 0



if __name__ == "__main__":
    raise RuntimeError("Not executable as standalone script")
