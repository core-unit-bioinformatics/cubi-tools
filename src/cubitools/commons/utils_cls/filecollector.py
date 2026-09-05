
import fnmatch as fnm
import functools as fnt
import os
import pathlib as pl
import sys

from cubitools.commons.enums import PathType

from cubitools.commons.utils_cls.file import File
from cubitools.commons.utils_cls.filesize import FileSize, FileSizeStats


class FileCollector:
    """The FileCollector class is responsible for collecting files from
    a directory tree based on specified inclusion and exclusion criteria.
    It provides methods to filter directories and files, collect file information,
    and generate statistics about the collected files.

    It's reason to exist is to collect files, so it is hardcoded that files
    that currently do not exist (case: broken symlinks if symlinks are not per se
    excluded) will be > SILENTLY < ignored / skipped over.
    """

    def __init__(self, exclude_dir: list[str]|None, exclude_file: list[str]|None,
                 include_dir: list[str]|None, include_file: list[str]) -> None:
        self._follow_symlink_dirs = False
        self.walked_dirs = dict()
        self._last_dir = None
        self._exclude_dir = self._init_matcher(exclude_dir, False, False)
        self._exclude_file = self._init_matcher(exclude_file, True, False)
        self._include_dir = self._init_matcher(include_dir, False, True)
        self._include_file = self._init_matcher(include_file, True, True)
        return None

    def _init_matcher(self, glob_patterns, match_filename, include):
        matching_functions = []
        if glob_patterns is None:
            # default matcher will be added below
            pass
        else:
            for glob_pattern in glob_patterns:
                if glob_pattern == PathType.hidden.name:
                    # check for: is hidden
                    matcher = self._get_match_hidden()
                elif glob_pattern == PathType.symbolic.name:
                    if match_filename:
                        pass
                    else:
                        # special setting for os.walk
                        if include:
                            self._follow_symlink_dirs = True
                        else:
                            self._follow_symlink_dirs = False
                    matcher = self._get_match_symlink()
                else:
                    # check for: fixed string match in fp
                    matcher = self._get_match_generic(glob_pattern)
                matching_functions.append(matcher)
        if not matching_functions:
            matcher = self._get_match_default(include)
            matching_functions.append(matcher)
        return matching_functions

    def _get_match_default(self, include):

        if include:
            def include_all(path) -> bool:
                """Default matcher for include check,
                always True, i.e. include everything

                Args:
                    path (str): file path or component thereof

                Returns:
                    bool: include/keep the path
                """
                return True
            return include_all
        else:
            def exclude_none(path) -> bool:
                """Default matcher for exclude check,
                always False, i.e. exclude nothing

                Args:
                    path (str): file path or component thereof

                Returns:
                    bool: exclude/drop the path
                """
                return False
            return exclude_none

    def _get_match_hidden(self):

        def is_hidden(file_path) -> bool:
            return pl.Path(file_path).name.startswith(".")

        return is_hidden

    def _get_match_symlink(self):

        def is_symlink(file_path) -> bool:
            return pl.Path(file_path).is_symlink()

        return is_symlink

    def _get_match_generic(self, pattern: str):

        def glob_match(glob_pat: str, path) -> bool:
            return fnm.fnmatch(path, glob_pat)

        partial = fnt.partial(glob_match, *(pattern,))
        return partial

    def keep_dirs(self, dir_paths: list[str]):
        """This method is specifically written to be compatible
        with `os.walk` in terms of filtering the list of subdirs
        in place. If not modified in place, `os.walk` will recurse
        into subdirectories that should not be visited.

        Args:
            dir_paths (list[str]): _description_

        Returns:
            _type_: _description_
        """
        delete_entries = []
        for idx, dir_path in enumerate(dir_paths):
            if any(check_exclude(dir_path) for check_exclude in self._exclude_dir):
                # any of the exclude checks triggered -> exclude
                delete_entries.append(idx)
                continue
            if not any(check_include(dir_path) for check_include in self._include_dir):
                # none of the include checks triggered -> exclude
                delete_entries.append(idx)
        # NB: crucial to delete entries in the list
        # from right to left, otherwise the index values
        # will be shifted if deleting from left to right
        # (low to high)
        for idx in sorted(delete_entries, reverse=True):
            del dir_paths[idx]
        return None

    def keep_files(self, filenames: list[str]) -> list[str]:

        retain_files = []
        for filename in filenames:
            if any(check_exclude(filename) for check_exclude in self._exclude_file):
                # any of the exclude checks triggered -> exclude
                continue
            if not any(check_include(filename) for check_include in self._include_file):
                # none of the include checks triggered -> exclude
                continue
            retain_files.append(filename)

        return retain_files

    def get_last_stats(self):

        if self._last_dir is None:
            return None
        else:
            return self.walked_dirs[self._last_dir]

    def get_stats(self, root_dir=None) -> FileSizeStats:

        if root_dir is not None:
            return self.walked_dirs[root_dir]

        total_files = 0
        total_size = 0
        min_size = sys.maxsize
        max_size = 0
        for _, dir_stats in self.walked_dirs.items():
            total_files += dir_stats.total_files
            total_size = dir_stats.total_size + total_size
            min_size = min(min_size, dir_stats.min_size)
            max_size = max(max_size, dir_stats.max_size)
        stats = FileSizeStats(
            total_files, FileSize(total_size),
            FileSize(min_size), FileSize(max_size)
        )
        return stats

    def collect_files(self, root_dir: pl.Path):
        """
        Collects files from the specified root directory.

        Args:
            root_dir (pl.Path): This is one of the user-supplied --archive-dirs
        Returns:
            list[File]: A list of File objects representing the collected files.
        """

        max_file_size = 0
        min_file_size = sys.maxsize
        total_file_size = 0
        collected_files = []
        for toplevel, subdirs, filenames in os.walk(root_dir, topdown=True, followlinks=self._follow_symlink_dirs):
            # NB: subdirs can be modified in-place to prune away parts of the
            # directory tree that we do not want; see
            # https://docs.python.org/3/library/os.html#os.walk
            self.keep_dirs(subdirs)
            filenames = self.keep_files(filenames)
            for filename in filenames:
                abs_path = pl.Path(toplevel, filename).absolute()
                # important: relative to archive/root dir
                rel_path = abs_path.relative_to(root_dir)
                fobj = File(abs_path=abs_path, rel_base=root_dir, rel_path=rel_path)
                if fobj._exists == 0:
                    # silently skip over files that do not exist
                    continue
                max_file_size = max(max_file_size, fobj.size)
                min_file_size = min(min_file_size, fobj.size)
                total_file_size += fobj.size
                collected_files.append(fobj)
        num_files = len(collected_files)
        if num_files == 0:
            min_file_size = FileSize(0)
        else:
            min_file_size = FileSize(min_file_size)
        max_file_size = FileSize(max_file_size)
        total_file_size = FileSize(total_file_size)

        self.walked_dirs[root_dir] = FileSizeStats(
            num_files, total_file_size,
            min_file_size, max_file_size
        )
        self._last_dir = root_dir
        raise
        return collected_files
