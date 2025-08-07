#!/usr/bin/env python3

import argparse as argp
import collections as col
import io
import os
import pathlib as pl
import random as rand
import statistics as stat
import sys
import time


def parse_command_line():

    parser = argp.ArgumentParser()

    parser.add_argument(
        "--repeat", "-r",
        type=int,
        default=3,
        dest="repeat"
    )

    parser.add_argument(
        "--size", "-s",
        type=int,
        default=int(1e10),
        dest="size",
        help="Default: ~10 GB"
    )

    args = parser.parse_args()

    return args


def dump_blob(file_path, size):

    buffer = io.BytesIO()
    buffer_start = time.perf_counter()
    buffer.write(os.urandom(size))
    buffer_end = time.perf_counter()
    with open(file_path, "wb") as dump:
        _ = dump.write(buffer.getvalue())
    dump_end = time.perf_counter()

    buffer_delta = buffer_end - buffer_start
    dump_delta = dump_end - buffer_end

    return buffer_delta, dump_delta


def main():

    print("-------")
    print("Python ", sys.version)
    print("-------")

    args = parse_command_line()

    my_wd = pl.Path(".").resolve()
    # assert we can write here...
    testfile = my_wd.joinpath("io-test.blob")
    with open(testfile, "wb"):
        pass
    os.remove(testfile)

    timings = col.defaultdict(list)
    for iter in range(args.repeat):
        run_start = time.perf_counter()
        buffer_time, dump_time = dump_blob(testfile, args.size)
        run_end = time.perf_counter()
        run_delta = run_end - run_start
        if iter == 0:
            file_size_byte = os.stat(testfile).st_size
            file_size_gb = round(file_size_byte / (1024**3), 3)
            print(f"Dumped file size: ~{file_size_gb} GB")
        os.remove(testfile)
        timings["run_total"].append(run_delta)
        timings["buffer_fill"].append(buffer_time)
        timings["disk_write"].append(dump_time)

    for operation, time_deltas in timings.items():
        print(f"=== {operation}")
        print(time_deltas)
        median_time = round(stat.median(time_deltas), 5)
        print(f"median time (sec.): {median_time}")
        if operation == "disk_write":
            gb_per_sec = round(file_size_gb / median_time, 3)
            print("--------")
            print(f"Estimated write speed: {gb_per_sec} GB/sec")

    return 0





if __name__ == "__main__":
    main()
