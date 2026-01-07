
import itertools as itt
import pathlib as pl

from cubitools.commons.env import CUBITOOLS_ENVIRONMENT as CT_ENV
from cubitools.commons.config import CUBITOOLS_CONFIG as CT_CONFIG
from cubitools.commons.enums import Compression, PathType, Checksum
from cubitools.commons.utils_cls.filesize import FileSize
from cubitools.commons.utils_cls.filecollector import FileCollector
from cubitools.commons.utils_cls.io_path import IOPath
from cubitools.commons.utils_cls.logging import CubiToolsLogger
import cubitools.commons.utils_func.checksums as ctchk
import cubitools.commons.utils_func.files as ctfiles



LOGGER_NAME = __name__
LOGGER = CubiToolsLogger(LOGGER_NAME)


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
        required=True,
        help=""
    )

    parser.add_argument(
        "--out-prefix", "-op",
        type=IOPath.output_prefix,
        dest="out_prefix",
        required=True,
        help=""
    )

    parser.add_argument(
        "--compress", "-c",
        type=Compression,
        choices=list(Compression.__members__.keys()),
        default=Compression.GZIP,
        dest="compression",
        help=f"Select tar compression tool. Default: {Compression.GZIP.name}"
    )

    parser.add_argument(
        "--checksums", "-chk",
        type=Checksum,
        nargs="*",
        choices=list(Checksum.__members__.keys()),
        default=[Checksum.MD5, Checksum.SHA256],
        dest="checksums",
        help=f"Select checksums to compute. Default: {Checksum.MD5, Checksum.SHA256}"
    )

    parser.add_argument(
        "--chunk-limit", "-lim",
        type=str,
        default="4t",
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

    parser.add_argument(
        "--exclude", "-excl",
        type=str,
        nargs="*",
        default=[PathType.HIDDEN.name, PathType.SYMBOLIC.name],
        dest="exclude",
        help=(
            "Exclude file paths matching ANY of these regular expressions "
            "or attributes. These arguments are checked first / before include. "
            "Default: HIDDEN and SYMBOLIC (= skip over hidden files and "
            "folders and symbolic links)."
        )
    )

    parser.add_argument(
        "--include", "-incl",
        type=str,
        nargs="*",
        default=None,
        dest="include",
        help=(
            "Include only file paths matching ANY of these regular expressions. "
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


def collect_file_paths(archive_dirs, file_collector):

    collected_files = dict()
    size_per_dir = dict()
    for arch_dir in archive_dirs:
        LOGGER.debug(f"Walking directory {arch_dir}")
        collected_files[arch_dir] = file_collector.collect_files(arch_dir)
        stats = file_collector.get_last_stats()
        size_per_dir[arch_dir] = stats.total_size
        LOGGER.debug(f"Files collected: {stats.total_files}")
        LOGGER.debug(f"Total file size: {stats.total_size.mb} mb")
        LOGGER.debug(f"Min. file size: {stats.min_size.mb} mb")
        LOGGER.debug(f"Max. file size: {stats.max_size.mb} mb")

    return collected_files, size_per_dir


def check_chunk_limit(chunk_limit, file_collector):

    stats = file_collector.get_stats()
    LOGGER.debug(f"Files collected: {stats.total_files}")
    LOGGER.debug(f"Total file size: {stats.total_size.mb} mb")
    LOGGER.debug(f"Min. file size: {stats.min_size.mb} mb")
    LOGGER.debug(f"Max. file size: {stats.max_size.mb} mb")

    if stats.max_size > chunk_limit:
        err_msg = (
            f"Your selected chunk limit of {chunk_limit} byte "
            f"(~{chunk_limit.gb} gb) is smaller than the largest "
            f"file discovered in in the input directories: {stats.max_size.gb} gb."
            "You need to increase the chunk limit or remove files larger "
            "than that from the input directories."
        )
        raise ValueError(err_msg)
    return None


def exec_arch_module(args):

    LOGGER.set_debug_logging(args.debug)
    CT_CONFIG.set_logger(LOGGER)

    chunk_limit = FileSize(args.chunk_limit)
    file_collector = FileCollector(args.include, args.exclude)

    LOGGER.debug("Collecting files...")
    collected_files, size_per_dir = collect_file_paths(args.archive_dirs, file_collector)

    if args.dry_run:
        LOGGER.info("Dry run set - skipping checksum computation")
    else:
        LOGGER.debug("Computing checksums...")
        ctchk.add_checksums_to_files(
            ctfiles.get_collected_files_iter(collected_files),
            args.checksums, args.jobs, LOGGER
        )


    return 0



if __name__ == "__main__":
    raise RuntimeError("Not executable as standalone script")
