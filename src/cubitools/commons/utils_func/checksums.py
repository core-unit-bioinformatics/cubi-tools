
from queue import Empty as QEmpty
import multiprocessing as mp
import time
import typing as typ

from cubitools.commons.enums import Checksum
from cubitools.commons.utils_cls.syscall import SysCallInterface
from cubitools.commons.utils_cls.file import File


def checksum_worker(inq, outq):


    chk_sci = dict()

    while 1:
        request = inq.get()
        if request is None:
            outq.put(None)
            break
        else:
            file_path, checksum_type = request
            try:
                sci = chk_sci[checksum_type]
            except KeyError:
                sci_exec = f"{checksum_type.name.lower()}sum"
                sci = SysCallInterface(executable=sci_exec)
                chk_sci[checksum_type] = sci
            checksum, _ = sci.run([file_path])
            checksum, _ = checksum.split()
            outq.put((request, checksum))
    return None


def add_checksums_to_files(files: list[File]|typ.Iterable[File], checksums: list[Checksum], jobs: int, logger):

    sync_man = mp.Manager()
    sendq = sync_man.Queue()
    recvq = sync_man.Queue()

    workers = [
        mp.Process(target=checksum_worker, args=(sendq, recvq))
        for _ in range(jobs)
    ]
    logger.debug(f"Initialized {jobs} worker processes")
    [p.start() for p in workers]

    try:
        num_files = len(files)  #type: ignore
    except TypeError:
        # this can happen if an iterator is passed
        # instead of a plain list, which makes sense
        # for very many fils
        num_files = None

    if num_files is None:
        logger.debug(
            "Adding files from iterator to processing queue w/ "
            f"{len(checksums)} checksum(s) requests for each."
        )
    else:
        logger.debug(
            f"Adding {num_files} files to processing queue w/ "
            f"{len(checksums)} checksum(s) requests for each."
        )

    for num_files, file in enumerate(files, start=1):
        for checksum in checksums:
            sendq.put((file.abs_path, checksum))

    if num_files is not None:
        logger.debug(f"Added {num_files} files to processing queue")

    logger.debug(f"Adding sentinels to processing queue")
    for _ in range(jobs):
        sendq.put(None)

    active_workers = jobs
    file_checksums = dict()
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
                logger.warning(warn_msg)
                # this is probably bad because not all
                # workers properly exited and put the
                # sentinel into the queue
                # => this here avoids that main is
                # waiting forever on dead children
                break
        if res is None:
            logger.debug(f"Remaining active workers: {active_workers}")
            active_workers -= 1
        else:
            file_checksums[res[0]] = res[1]
        if active_workers < 1:
            break

    for p in workers:
        if p.is_alive():
            logger.debug("Worker still alive - joining/terminating")
            p.join(0.5)
            p.terminate()

    # this should typically never be triggered because an error
    # in one of the workers / system calls would be propagated

    if num_files is None or num_files < 1:
        raise RuntimeError("No checksums to compute")

    n_should = num_files * len(checksums)
    n_has = len(file_checksums)
    if n_has != n_should:
        missing = n_should - n_has
        err_msg = (
            "No all checksums could be computed. "
            f"Success: {n_has} - fail: {missing} (total: {n_should})"
        )
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    for file in files:
        for checksum in checksums:
            attr_name = checksum.name.lower()
            setattr(file, attr_name, file_checksums[(file.abs_path, checksum)])

    return None



