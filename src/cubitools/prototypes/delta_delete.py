#!/usr/bin/env python3

import argparse as argp
import collections as col
import csv
import datetime as dt
import getpass
import os
import pathlib as pl
import pwd


VERBOSE_OUTPUT = False
LIST_FILE_OPS = False
ACTIVE_USER = None

EXAMPLE_CALL = (
    "./delta_delete.py -l *_manifest.tsv "
    " -b manifest_backup.tsv "
    "-del-ext .bam .pbi .bai .pod5 .fast5 "
    "-e -s bck-mhpc [--delete-run]"
)

DESCRIPTION = (
    "Operates on standard EBI manifest files, i.e. "
    "tab-separated 3-column text tables... "
    "(1st column) file path [can be relative] "
    "(2nd column) file size in byte "
    "(3rd column) file MD5 checksum"
    " // "
    "Creates a dot file for each deleted file as history record."
)


def parse_command_line():

    parser = argp.ArgumentParser(usage=EXAMPLE_CALL, description=DESCRIPTION)

    parser.add_argument(
        "--backup-manifest", "-b",
        type=lambda fp: pl.Path(fp).resolve(strict=True),
        dest="backup_manifest",
        help="Manifest file(s) of backup destination",
        nargs="+"
    )

    parser.add_argument(
        "--local-manifest", "-l",
        type=lambda fp: pl.Path(fp).resolve(strict=True),
        dest="local_manifest",
        help="Manifest file(s) of local storage",
        nargs="+"
    )

    parser.add_argument(
        "--file-ext-to-delete", "-del-ext",
        type=str,
        default=None,
        dest="file_ext_to_delete",
        nargs="*",
        help=(
            "Space-sep list of file extension to delete, e.g., .bam .pbi .bai"
            " // Default: None (= delete all)"
        )
    )

    parser.add_argument(
        "--delete-run",
        action="store_true",
        default=False,
        dest="delete_run",
        help="Execute; delete files locally that exist on backup location."
    )

    parser.add_argument(
        "--dot-shadow-ext", "-s",
        type=str,
        default=".backup",
        dest="dot_shadow_ext",
        help="Set file extension for dot shadow files. Default: .backup"
    )

    parser.add_argument(
        "--explain", "-e",
        action="store_true",
        dest="explain",
        help="Explain what's happening - verbose output"
    )

    parser.add_argument(
        "--list-file-ops", "-o",
        action="store_true",
        dest="list_file_ops",
        help="On top of verbose output, list all file ops (deletions)."
    )

    args = parser.parse_args()

    return args


def create_dot_shadow_file_path(data_file, shadow_ext):

    shadow_ext = "." + shadow_ext.strip(".")

    file_name = data_file.name
    new_path = data_file.parent.joinpath(
        f".{file_name}{shadow_ext}"
    )
    return new_path


def read_manifest_file(manifest_file):

    assert manifest_file.suffix == ".tsv"

    file_entries = dict()
    with open(manifest_file, "r", newline="") as table:
        reader = csv.DictReader(
            table, fieldnames=["file_path", "file_size", "checksum"],
            delimiter="\t"
        )
        for row in reader:
            row["file_path"] = pl.Path(row["file_path"])
            file_entries[row["checksum"]] = row
    return file_entries


def merge_manifest_files(file_paths):

    manifest_entries = dict()
    for file_path in file_paths:
        this_file = read_manifest_file(file_path)
        is_disjoint = all(chk not in manifest_entries for chk in this_file.keys())
        if not is_disjoint:
            raise RuntimeError(f"Duplicate checksums - currently loading: {this_file}")
        manifest_entries.update(this_file)
    return manifest_entries


def byte_to_gbyte(size_in_byte):

    gigabyte = round(size_in_byte / 1024 ** 3, 1)
    return gigabyte


def get_file_owner(file_path):
    return pwd.getpwuid(os.stat(file_path).st_uid).pw_name


def print_file_report(file_exts, ext_sizes=None):

    if ext_sizes is None:
        select_op = "ign"
    else:
        select_op = "del"

    for (file_ext, ext_op) in sorted(file_exts.keys()):
        if ext_op != select_op:
            continue
        num = file_exts[(file_ext, ext_op)]
        print(f"{ext_op} files of type {file_ext}: {num}")
        if ext_sizes is not None:
            total_size = ext_sizes[file_ext]
            size_gb = byte_to_gbyte(total_size)
            print(f" --- will free: ~{size_gb} GB")
    return


def find_files_to_delete(local_files, backup_files, file_ext_to_del):

    delete_all = file_ext_to_del is None
    if not delete_all:
        assert isinstance(file_ext_to_del, list)
        # normalize for use with pathlib.Path().suffix
        file_ext_to_del = [f".{fext.strip('.')}" for fext in file_ext_to_del]

    files_to_delete = []
    ext_counter = col.Counter()
    size_counter = col.Counter()
    for checksum, file_info in local_files.items():
        if checksum not in backup_files:
            continue
        file_ext = file_info["file_path"].suffix
        if not file_ext:
            file_ext = "no-file-ext"
        if delete_all:
            ext_counter[(file_ext, "del")] += 1
            files_to_delete.append(file_info)
            size_counter[file_ext] += int(file_info["file_size"])
        elif file_ext in file_ext_to_del:
            ext_counter[(file_ext, "del")] += 1
            files_to_delete.append(file_info)
            size_counter[file_ext] += int(file_info["file_size"])
        else:
            ext_counter[(file_ext, "ign")] += 1

    if VERBOSE_OUTPUT:
        print(" ====== ")
        print(" Ignored files: ")
        print_file_report(ext_counter)
        print(" ===== ")
        print(" Files to delete: ")
        print_file_report(ext_counter, size_counter)
        print(" ===== ")

    return files_to_delete


def augment_file_info(files_to_delete, shadow_ext):

    ts = dt.datetime.now().strftime("%Y%m%dT%H%M%S")

    remaining_files = []
    for file_info in files_to_delete:
        try:
            full_path = file_info["file_path"].resolve(strict=True)
            file_owner = get_file_owner(full_path)
            if file_owner != ACTIVE_USER:
                raise PermissionError(f"Wrong owner: {file_owner} / {full_path}")
        except FileNotFoundError:
            if VERBOSE_OUTPUT:
                print(f"File no longer exists: {file_info['file_path']}")
                continue
        except PermissionError as perm_err:
            if VERBOSE_OUTPUT:
                print(str(perm_err))
                continue
        else:
            shadow_file = create_dot_shadow_file_path(
                full_path, shadow_ext
            )
            shadow_content = (
                f"timestamp\t{ts}\n"
                f"size\t{file_info['file_size']}\n"
                f"md5\t{file_info['checksum']}\n"
                f"user\t{ACTIVE_USER}\n"
            )
            remaining_files.append(
                (full_path, shadow_file, shadow_content)
            )
            if VERBOSE_OUTPUT and LIST_FILE_OPS:
                print(f"Will delete: {full_path}")
                print(f"Will create: {shadow_file}")
    return remaining_files


def execute_file_delete(files_to_delete):

    for del_file, shadow_file, shadow_content in files_to_delete:
        with open(shadow_file, "w") as dump:
            _ = dump.write(shadow_content)
        os.unlink(del_file)
    return


def main():

    args = parse_command_line()

    global ACTIVE_USER
    ACTIVE_USER = getpass.getuser()

    if args.explain:
        global VERBOSE_OUTPUT
        VERBOSE_OUTPUT = True
    if args.list_file_ops:
        global LIST_FILE_OPS
        LIST_FILE_OPS = True

    local_entries = merge_manifest_files(args.local_manifest)
    backup_entries = merge_manifest_files(args.backup_manifest)

    if VERBOSE_OUTPUT:
        print(f"Manifest entries - local: {len(local_entries)}")
        print(f"Manifest entries - backup: {len(backup_entries)}")

    files_to_delete = find_files_to_delete(
        local_entries, backup_entries,
        args.file_ext_to_delete
    )
    if VERBOSE_OUTPUT:
        print(f"Collected {len(files_to_delete)} files to delete")

    files_to_delete = augment_file_info(files_to_delete, args.dot_shadow_ext)
    if VERBOSE_OUTPUT:
        print(f"After FS exists check, {len(files_to_delete)} files remain to delete")

    if args.delete_run:
        if VERBOSE_OUTPUT:
            print(" === This is a delete run === ")
            execute_file_delete(files_to_delete)

    return 0




if __name__ == "__main__":
    main()
