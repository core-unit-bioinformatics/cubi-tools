
import collections as col
import math
import multiprocessing as mp
import os
import pathlib as pl
from queue import Empty as QEmpty
import time

from cubitools.commons.env import CUBITOOLS_ENVIRONMENT as CT_ENV
from cubitools.commons.config import CUBITOOLS_CONFIG as CT_CONFIG
from cubitools.commons.enums import Compression, PathType, PathComponent, Checksum, FileManifestType, FileManifestExt
from cubitools.commons.utils_cls.file import File
from cubitools.commons.utils_cls.filesize import FileSize
from cubitools.commons.utils_cls.filecollector import FileCollector
from cubitools.commons.utils_cls.io_path import IOPath
from cubitools.commons.utils_cls.logging import CubiToolsLogger
from cubitools.commons.utils_cls.syscall import SysCallInterface
import cubitools.commons.utils_func.checksums as ctchk
import cubitools.commons.utils_func.files as ctfiles



LOGGER_NAME = __name__
LOGGER = CubiToolsLogger(LOGGER_NAME)


ArchiveWorkPackage = col.namedtuple(
    "ArchiveWorkPackage",
    [
        "arch_dir", "batch_num", "compression",
        "out_prefix", "scratch_dir", "arch_files",
        "manifest", "no_manifest_header", "manifest_only",
        "dry_run", "cleanup"
    ]
)


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

    compress_members = list(Compression.__members__)
    parser.add_argument(
        "--compress", "-c",
        type=str,
        choices=compress_members,
        default=Compression.gzip.name,
        dest="compression",
        help=f"Select tar compression tool. Default: {Compression.gzip.name}"
    )

    checksum_members = list(Checksum.__members__)
    parser.add_argument(
        "--checksums", "-chk",
        type=str,
        nargs="*",
        choices=checksum_members,
        default=[Checksum.md5.name, Checksum.sha256.name],
        dest="checksums",
        help=f"Select checksum(s) to compute. Default: {Checksum.md5.name, Checksum.sha256.name}"
    )

    parser.add_argument(
        "--chunk-limit", "-lim",
        type=str,
        default="1t",
        dest="chunk_limit",
        help=(
            "Limit the size of the resulting tar archive, i.e. "
            "create several chunks not larger than this limit "
            "if necessary. Set to -1 to deactivate. "
            "Default: 1t[erabyte]"
        )
    )

    parser.add_argument(
        "--scratch-dir", "-s",
        type=IOPath.output_dir,
        default=None,
        dest="scratch_dir",
        help=(
            "Use this directory as destination for all tar and metadata files. "
            "Setting this option may be required if the source file system has "
            "not enough free space to create the tar archives. Usually, this "
            "makes most sense in conjunction with the '--cleanup' option."
        )
    )

    manifest_members = list(FileManifestType.__members__)
    parser.add_argument(
        "--manifest", "-m",
        type=str,
        choices=manifest_members,
        default=FileManifestType.complete.name,
        dest="manifest",
        help=(
            "Select the type of the file manifest to be created: "
            "(1) complete: list relative file path, size and all computed checksums "
            "(2) minimal: list only file name, size and shortest checksum available (typically, that is md5) "
            "(3) coreutils: list relative file path and checksum (format is compatible to GNU coreutils md5sum, sha1sum etc.) "
            "(4) skip: do not create a file manifest (discouraged). "
            f"Default: {FileManifestType.complete.name}"
        )
    )

    parser.add_argument(
        "--manifest-only", "-mly",
        action="store_true",
        default=False,
        dest="manifest_only",
        help="Only create the file manifest(s) and skip creating the tar archive(s). Default: False"
    )

    parser.add_argument(
        "--no-manifest-header", "-nhd",
        action="store_true",
        default=False,
        dest="no_manifest_header",
        help="Do not add a header row to the file manifest output. Default: False"
    )

    parser.add_argument(
        "--exclude-dir", "-ex-dir",
        type=str,
        nargs="*",
        default=[PathType.hidden.name, PathType.symbolic.name],
        dest="exclude_dir",
        help=(
            "Exclude directories matching ANY of these glob patterns "
            "or attributes. These arguments are checked before include. "
            "Default: 'hidden' and 'symbolic' (= skip over hidden directories and "
            "do not walk into/follow symbolic link directories)."
        )
    )

    parser.add_argument(
        "--exclude-file", "-ex-file",
        type=str,
        nargs="*",
        default=[PathType.hidden.name, PathType.symbolic.name],
        dest="exclude_file",
        help=(
            "Exclude files (by name) matching ANY of these glob patterns "
            "or attributes. These arguments are checked before include. "
            "Default: 'hidden' and 'symbolic' (= skip over hidden files and "
            "folders and symbolic links)."
        )
    )

    parser.add_argument(
        "--include-dir", "-in-dir",
        type=str,
        nargs="*",
        default=None,
        dest="include_dir",
        help=(
            "Include only directories matching ANY of these glob patterns. "
            "Default: None (= include all directories that are NOT excluded)."
        )
    )

    parser.add_argument(
        "--include-file", "-in-file",
        type=str,
        nargs="*",
        default=None,
        dest="include_file",
        help=(
            "Include only files (by name) matching ANY of these glob patterns. "
            "Default: None (= include all files that are NOT excluded)."
        )
    )

    parser.add_argument(
        "--cleanup", "-clean",
        action="store_true",
        default=False,
        dest="cleanup",
        help="Delete the archived files and (empty) folders."
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
            "file discovered in in the input directories: "
            f"{stats.max_size.gb} gb / {stats.max_size.size} b. "
            "You need to increase the chunk limit or remove files larger "
            "than that from the input directories."
        )
        raise ValueError(err_msg)
    return None


def group_files_in_batches(archive_files, chunk_limit, arch_dir_sizes):

    batch_num = 1
    batch_size = 0
    file_batches = dict()
    total_files = 0
    batched_files = 0
    current_batch = []  # just to calm pylint in assert below
    for arch_dir, arch_files in archive_files.items():
        total_files += len(arch_files)
        current_batch = []
        arch_dir_size = arch_dir_sizes[arch_dir]
        LOGGER.debug(
            f"Batching files from: {arch_dir} "
            f"(size: {arch_dir_size} b / {len(arch_files)} files)"
        )
        if arch_dir_size < chunk_limit:
            active_limit = chunk_limit
        else:
            split_equal = math.ceil(arch_dir_size / chunk_limit)
            _fudge_factor = 1.1
            # This is an empirical factor because a hard div here
            # typically leads to 'one more' batch containing only a
            # few files due to the unknown distribution of file
            # sizes per batch. Slightly increasing the active limit
            # leads to a more balanced distribution of files per batch.
            active_limit = min(chunk_limit, math.ceil(arch_dir_size / split_equal * _fudge_factor))
        LOGGER.debug(f"Batch size limit: {active_limit}")
        for arch_file in arch_files:
            if batch_size + arch_file.size > active_limit:
                batched_files += len(current_batch)
                LOGGER.debug(f"Middle batch: {batch_num} / num files: {len(current_batch)}")
                assert len(current_batch) > 0
                file_batches[(arch_dir, batch_num, batch_size)] = current_batch
                batch_num += 1
                # this file goes into the new batch
                current_batch = [arch_file]
                batch_size = arch_file.size
            else:
                batch_size += arch_file.size
                # append to current batch
                current_batch.append(arch_file)
        if len(current_batch) > 0:
            # NB: the batching operation works on a per-folder
            # level to group files together that came from
            # the same folder, hence this should typically
            # be true because we have reached the end of
            # arch_files (end of iter) above
            LOGGER.debug(f"Final batch: {batch_num} / num files: {len(current_batch)}")
            file_batches[(arch_dir, batch_num, batch_size)] = current_batch
            batch_num += 1
            batch_size = 0
            batched_files += len(current_batch)
            current_batch = []

    assert len(current_batch) == 0

    # after this, it should hopefully not happen
    # that we lose files in any subsequent operation
    assert batched_files == total_files, f"{total_files} / {batched_files}"

    return file_batches


def write_tar_file_listing(work_package):
    """This function writes a list of files into
    a fofn file that is passed to tar via the -T option.
    All paths in the file are relative to parent
    of 'arch_dir'
    """

    # NB: this listing should normally result in a small-ish
    # file that we always write into the parent directory of
    # the archive target directory; if the file system is really
    # at 100% capacity, this will lead to an early fail
    # in the process, unfortunately.
    out_prefix_name = work_package.out_prefix.name
    if work_package.batch_num == 0:
        infix = ""
    else:
        infix = f"part{work_package.batch_num}."

    # for the case of several input archive dirs,
    # we want to make it easier to identify the source
    # of each file by setting the root-level of the
    # relative path to the parent of the arch dir
    root_level = work_package.arch_dir.parent

    basename = f"{out_prefix_name}.{infix}"
    file_ext = "arch-file-listing.fofn"
    file_name = basename + file_ext

    fofn_file = root_level.joinpath(file_name)

    relative_paths = []
    for file in work_package.arch_files:
        assert file.rel_base == work_package.arch_dir
        relative_paths.append(file.get_fofn_entry(PathComponent.parent))

    if work_package.manifest_only:
        # won't create the archive
        pass
    elif work_package.dry_run:
        # don't create any output
        pass
    else:
        with open(fofn_file, "w") as listing:
            _ = listing.write("\n".join(sorted(relative_paths)) + "\n")

    return fofn_file, basename


def manifest_has_header(manifest_file):
    """manifest_has_header _summary_

    Args:
        manifest_file (_type_): _description_
    """
    try:
        with open(manifest_file, "r") as table:
            first_line = table.readline().strip().split()
            if len(first_line) < 3:
                # this must be a coreutils-style manifest,
                # which does not have a header
                return False
            # 2nd column is always size, i.e. an integer
            # if the file does not have a header
            _ = int(first_line[1])
    except ValueError:
        return True
    else:
        return False


def write_file_manifest(basename, work_package):
    """write_file_manifest _summary_

    Args:
        fofn_file (_type_): _description_
        work_package (_type_): _description_
    """
    manifest_type = FileManifestType[work_package.manifest]
    if manifest_type == FileManifestType.skip:
        return None

    manifest_ext = getattr(FileManifestExt, work_package.manifest)
    file_name = basename + manifest_ext
    manifest_file = work_package.out_prefix.parent.joinpath(file_name)

    manifest_header = None
    manifest_rows = []

    for arch_file in work_package.arch_files:
        manifest_header, manifest_row = arch_file.get_manifest_line(
            manifest_type
        )
        manifest_rows.append(manifest_row)

    if not work_package.dry_run:
        with open(manifest_file, "w") as table:
            if work_package.no_manifest_header:
                pass
            else:
                assert manifest_header is not None
                _ = table.write("\t".join(manifest_header) + "\n")

            _ = table.write("\n".join(
                "\t".join(row) for row in manifest_rows
            ) + "\n")

    return manifest_file


def determine_tar_out_paths(basename, work_package):
    """determine_tar_out_paths _summary_

    Args:
        basename (_type_): _description_
        work_package (_type_): _description_

    Returns:
        _type_: _description_
    """
    use_compression = Compression[work_package.compression]
    file_ext = f"tar.{use_compression.name}"
    file_name = basename + file_ext

    scratch_out = None
    if work_package.scratch_dir is not None:
        scratch_out = work_package.scratch_dir.joinpath(file_name)
        scratch_out.parent.mkdir(exist_ok=True, parents=True)
    final_out = work_package.out_prefix.parent.joinpath(file_name)
    final_out.parent.mkdir(exist_ok=True, parents=True)

    return scratch_out, final_out


def perform_cleanup(files_to_delete, remove_dirs=None):
    """perform_cleanup _summary_

    Args:
        files_to_delete (_type_): _description_
    """
    directories = set()
    for file in files_to_delete:
        if file is None:
            continue
        try:
            if isinstance(file, str) or isinstance(file, pl.Path):
                os.unlink(file)
                directories.add(pl.Path(file).parent)
            if isinstance(file, File):
                file.delete()
                assert file.abs_path is not None  # calm pylint
                directories.add(file.abs_path.parent)
        except (IOError, FileNotFoundError):
            continue

    if remove_dirs is not None:
        dirs_by_length = sorted(directories, key=lambda d: len(str(d)), reverse=True)
        prefix = str(remove_dirs)
        # start with longest dirs, are either empty or not
        for directory in dirs_by_length:
            # safeguarding here: we only remove dirs that are prefixed
            # with the archive dir - avoid accidentally deleting something
            # from another directory context
            if not str(directory).startswith(prefix):
                continue
            try:
                os.rmdir(directory)
            except (IOError, OSError) as exc:
                continue
    return


def archive_worker(recvq, sendq):

    to_delete = []
    manifest_file = None
    final_out = None
    while 1:
        work_pkg = recvq.get()
        if work_pkg is None:
            sendq.put(None)
            break
        fofn_file, basename = write_tar_file_listing(work_pkg)
        to_delete.append(fofn_file)
        scratch_out, final_out = determine_tar_out_paths(basename, work_pkg)
        if scratch_out is not None:
            tar_target = scratch_out
        else:
            tar_target = final_out

        if work_pkg.manifest_only:
            sci = SysCallInterface(working_dir=work_pkg.arch_dir.parent, dry_run=True)
        else:
            sci = SysCallInterface(working_dir=work_pkg.arch_dir.parent, dry_run=work_pkg.dry_run)
        try:
            sci.run(
                [
                    "tar", "--create", "--auto-compress", "--verbatim-files-from",
                    "-T", str(fofn_file), "-f", str(tar_target)
                ]
            )
            manifest_file = write_file_manifest(basename, work_pkg)
        except Exception:
            # we are assuming that the generated tar archive
            # is corrupt in some way
            to_delete.append(tar_target)
            to_delete.append(manifest_file)
            if not work_pkg.dry_run:
                perform_cleanup(to_delete)
            raise

        if scratch_out is not None:
            try:
                sci.run(
                    [
                        "rsync", "--checksum", str(scratch_out), str(final_out)
                    ]
                )
            except Exception:
                # NB: here, we are keeping the generated tar archive
                if not work_pkg.dry_run:
                    perform_cleanup(to_delete)
                raise
            else:
                to_delete.append(scratch_out)

        if not work_pkg.dry_run:
            perform_cleanup(to_delete)

        assert final_out is not None
        if not (work_pkg.dry_run or work_pkg.manifest_only):

            tar_file = File(abs_path=final_out.resolve(strict=True))

            LOGGER.debug("Comuting checksum sha256 for tar archive")
            ctchk.add_checksum_to_file(tar_file, Checksum.sha256, LOGGER)

            tar_chk = str(tar_file.abs_path) + ".sha256"
            LOGGER.debug(f"Dumping checksum file for tar to: {tar_chk}")

            with open(tar_chk, "w") as chk_file:
                _ = chk_file.write(f"{tar_file.sha256}  {final_out.name}\n")

        if work_pkg.cleanup and not work_pkg.dry_run:
            perform_cleanup(work_pkg.arch_files, remove_dirs=work_pkg.arch_dir)

    return None


def archive_folders(file_batches, args):

    sync_man = mp.Manager()
    sendq = sync_man.Queue()
    recvq = sync_man.Queue()

    workers = [
        mp.Process(target=archive_worker, args=(sendq, recvq))
        for _ in range(args.jobs)
    ]
    LOGGER.debug(f"Initialized {len(workers)} worker processes")
    [p.start() for p in workers]

    for (sub_folder, batch_num, _), arch_files in file_batches.items():
        if len(file_batches) == 1:
            bnum = 0
        else:
            bnum = batch_num
        work_pkg = ArchiveWorkPackage(
            sub_folder, bnum, args.compression,
            args.out_prefix, args.scratch_dir, arch_files,
            args.manifest, args.no_manifest_header, args.manifest_only,
            args.dry_run, args.cleanup
        )
        sendq.put(work_pkg)

    LOGGER.debug("Adding sentinels to processing queue")
    for _ in workers:
        sendq.put(None)

    active_workers = len(workers)
    while 1:
        try:
            res = recvq.get_nowait()
        except QEmpty:
            if any(p.is_alive() for p in workers):
                # this is fine, computing checksums
                # can take a while...
                time.sleep(1)
                continue
            else:
                warn_msg = (
                    "No worker processes left alive but at least "
                    "one did not exit properly. Breaking..."
                )
                LOGGER.warning(warn_msg)
                # this is probably bad because not all
                # workers properly exited and put the
                # sentinel into the queue
                # => this here avoids that main is
                # waiting forever on dead children
                break
        if res is None:
            LOGGER.debug(f"Remaining active workers: {active_workers}")
            active_workers -= 1
        if active_workers < 1:
            LOGGER.debug("All workers done - breaking out of while loop")
            break

    for p in workers:
        if p.is_alive():
            LOGGER.debug("Worker still alive - joining/terminating")
            p.join(0.5)
            p.terminate()

    return None


def exec_arch_module(args):

    LOGGER.set_debug_logging(args.debug)
    CT_CONFIG.set_logger(LOGGER)

    if not args.cleanup and args.scratch_dir is not None:
        warn_msg = (
            "You set a scratch directory path w/o the '--cleanup' option. "
            "This will result in an extra file copy step for the generated "
            "tar archive files without deleting the archived files beforehand. "
            "This may be intended, but creates I/O overhead."
        )
        LOGGER.warning(warn_msg)

    chunk_limit = FileSize(args.chunk_limit)
    file_collector = FileCollector(
        args.exclude_dir, args.exclude_file,
        args.include_dir, args.include_file
    )

    LOGGER.debug("Collecting files...")
    collected_files, size_per_dir = collect_file_paths(args.archive_dirs, file_collector)

    required_checksums = [Checksum[chksum] for chksum in args.checksums]

    manifest_type = FileManifestType[args.manifest]
    if manifest_type == FileManifestType.coreutils:
        if len(required_checksums) > 1:
            LOGGER.debug(
                "You selected a coreutils-style manifest but requested "
                "more than one checksum to be computed. Please specify "
                "only one checksum for this manifest type."
            )
            raise ValueError(
                f"Coreutils-style manifest requires exactly one checksum to be computed: {required_checksums}"
            )
        if args.no_manifest_header:
            pass
        else:
            LOGGER.warning(
                "You selected a coreutils-style manifest, which must not have "
                "a header row by construction. The '--no-manifest-header' option "
                "will be set to 'True' automatically."
            )
            setattr(args, "no_manifest_header", True)

    # important to check for feasible chunk limit before
    # the checksum computation (potentially) starts
    check_chunk_limit(chunk_limit, file_collector)

    if args.dry_run:
        LOGGER.info("Dry run set - skipping checksum computation")
    else:
        # NB: the file objects in 'collected_files' are updated
        # in place with the respective checksum(s)
        LOGGER.debug("Computing checksums...")
        ctchk.add_checksums_to_files(
            ctfiles.get_files_iter(collected_files),
            required_checksums, args.jobs, LOGGER
        )

    file_batches = group_files_in_batches(collected_files, chunk_limit, size_per_dir)
    _ = archive_folders(file_batches, args)

    return 0



if __name__ == "__main__":
    raise RuntimeError("Not executable as standalone script")
