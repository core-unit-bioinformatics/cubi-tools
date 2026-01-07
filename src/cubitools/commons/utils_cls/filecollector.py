
import functools as fnt
import os
import pathlib as pl
import sys

from cubitools.commons.enums import PathType

from cubitools.commons.utils_cls.file import File
from cubitools.commons.utils_cls.filesize import FileSize, FileSizeStats


class FileCollector:

    def __init__(self, include: list[str], exclude: list[str]) -> None:
        if include is None:
            self.include_match = self._init_matcher([], True)
        else:
            self.include_match = self._init_matcher(include, True)
        if exclude is None:
            self.exclude_match = []
        else:
            self.exclude_match = self._init_matcher(exclude)
        self.walked_dirs = dict()
        self._last_dir = None
        return None

    def _init_matcher(self, fixed_exprs: list[str], add_default=False):
        matching_functions = []
        for fixed_expr in fixed_exprs:
            if fixed_expr.upper() == PathType.HIDDEN.name:
                # check for: is hidden
                matcher = self._get_match_hidden()
            elif fixed_expr.upper() == PathType.SYMBOLIC.name:
                # check for: is symbolic
                matcher = self._get_match_symlink()
            else:
                # check for: fixed string match in fp
                matcher = self._get_match_generic(fixed_expr)
            matching_functions.append(matcher)
        if not matching_functions and add_default:
             matcher = self._get_match_default()
             matching_functions.append(matcher)
        return matching_functions

    def _get_match_default(self):

        def is_match(file_path) -> bool:
            return True

        return is_match

    def _get_match_hidden(self):

        def is_hidden(file_path) -> bool:
            return pl.Path(file_path).name.startswith(".")

        return is_hidden

    def _get_match_symlink(self):

        def is_symlink(file_path) -> bool:
            return pl.Path(file_path).is_symlink()

        return is_symlink

    def _get_match_generic(self, fixed_expr: str):

        def contains_match(fixed_expr: str, file_path: pl.Path) -> bool:
            return fixed_expr in str(file_path)

        partial = fnt.partial(contains_match, *(fixed_expr,))
        return partial

    def _exclude(self, file_path) -> bool:
        # NB here: any([]) is False
        return any(match_fun(file_path) for match_fun in self.exclude_match)

    def _include(self, file_path) -> bool:
        # NB here: any([]) is False
        return any(match_fun(file_path) for match_fun in self.include_match)

    def keep_file(self, file_path) -> bool:
        if self._exclude(file_path):
            return False
        elif self._include(file_path):
            return True
        else:
            return False

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
            total_size += dir_stats.total_size
            min_size = min(min_size, dir_stats.min_size)
            max_size = max(max_size, dir_stats.max_size)
        stats = FileSizeStats(
            total_files, FileSize(total_size),
            FileSize(min_size), FileSize(max_size)
        )
        return stats

    def collect_files(self, root_dir: pl.Path):

        max_file_size = 0
        min_file_size = sys.maxsize
        total_file_size = 0
        collected_files = []
        for toplevel, subdirs, filenames in os.walk(root_dir, topdown=True, followlinks=False):
            # NB: subdirs can be modified in-place to prune away parts of the
            # directory tree that we do not want; see
            # https://docs.python.org/3/library/os.html#os.walk
            subdirs = [subdir for subdir in subdirs if not self._exclude(subdir)]
            keep_files = [fn for fn in filenames if self.keep_file(fn)]
            for filename in keep_files:
                abs_path = pl.Path(toplevel, filename)
                # important: relative to archive/root dir
                rel_path = abs_path.relative_to(root_dir)
                fobj = File(abs_path=abs_path, rel_base=root_dir, rel_path=rel_path)
                max_file_size = max(max_file_size, fobj.size)
                min_file_size = min(min_file_size, fobj.size)
                total_file_size += fobj.size
                collected_files.append(fobj)
        num_files = len(collected_files)
        if num_files == 0:
            min_file_size = 0
        else:
            min_file_size = FileSize(min_file_size)
        max_file_size = FileSize(max_file_size)
        total_file_size = FileSize(total_file_size)

        self.walked_dirs[root_dir] = FileSizeStats(
            num_files, total_file_size,
            min_file_size, max_file_size
        )
        self._last_dir = root_dir

        return collected_files
