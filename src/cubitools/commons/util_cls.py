
import collections as col
import dataclasses as dcl
import functools as fnt
import math
import os
import pathlib as pl
import re
import sys
import typing

from cubitools.commons.enums import FileSizeUnit, PathType


FileSizeStats = col.namedtuple(
    "FileSizeStats",
    field_names=["total_files", "total_size", "min_size", "max_size"]
)


class FileSize:

    __slots__ = ["size", "b", "kb", "mb", "gb", "tb"]

    def __init__(self, file_size):
        if isinstance(file_size, str):
            if file_size == "-1":
                self.size = sys.maxsize
            else:
                self.size = self._string_to_byte(file_size)
        elif isinstance(file_size, int):
            if file_size < 0:
                self.size = sys.maxsize
            else:
                self.size = file_size
        elif isinstance(file_size, float):
            if file_size < 0:
                self.size = sys.maxsize
            else:
                self.size = int(round(file_size, 0))
        else:
            raise TypeError(f"Cannot process type of file size: {file_size} / {type(file_size)}")
        for i in range(len(FileSizeUnit)):
            fsu = FileSizeUnit(i)
            assert fsu.value == i
            size_unit = self._to_unit(fsu.value)
            setattr(self, fsu.name, size_unit)
        return None

    def __str__(self):
        return f"{self.size}"

    def __repr__(self):
        return f"{self.size}"

    def __eq__(self, other) -> bool:
        return self.size == other.size

    def __ne__(self, other) -> bool:
        return self.size != other.size

    def __lt__(self, other) -> bool:
        return self.size < other.size

    def __le__(self, other) -> bool:
        return self.size <= other.size

    def __gt__(self, other) -> bool:
        return self.size > other.size

    def __ge__(self, other) -> bool:
        return self.size >= other.size

    def __add__(self, other: FileSize) -> FileSize:  #type: ignore
        # https://peps.python.org/pep-0484/
        return FileSize(self.size + other.size)  #type: ignore

    def __add__(self, other: int) -> int:
        return self.size + other

    def _string_to_byte(self, file_size: str):
        """Take a unit-suffixed string and convert it
        to a number that is set as the 'size' attribute
        of the class instance and that represents the
        file size in byte.

        Args:
            file_size (str): File size with unit suffix (k, m, g, t)

        Raises:
            ValueError: if the string does not have a unit suffix

        Returns:
            int: file size in byte
        """
        unit_names = list(FileSizeUnit.__members__.keys())
        unit_regexp = "(" + "|".join(unit_names) + ")"
        file_size = file_size.lower()
        match_unit = re.search(unit_regexp, file_size)
        if match_unit is None:
            raise ValueError(f"Cannot identify size unit in file size string: {file_size}")
        unit_start, unit_end = match_unit.span()
        unit = file_size[unit_start:unit_end]
        number = float(file_size[:unit_start])
        power = FileSizeUnit[unit].value
        size_in_byte = self._number_to_byte(number, power)
        return size_in_byte

    def _number_to_byte(self, file_size, power):
        size_in_byte = file_size * math.pow(1024, power)
        size_in_byte = int(round(size_in_byte, 0))
        return size_in_byte

    def _to_unit(self, power):
        size_in_unit = self.size / math.pow(1024, power)
        if size_in_unit < 1:
            size_in_unit = round(size_in_unit, 5)
        return size_in_unit

class File:
    _abs_path: pl.Path|None = None
    _rel_path: pl.Path|None = None
    _rel_base: pl.Path|None = None
    _exists: int|None = None
    _size: FileSize|None = None
    _md5: str|None = None
    _sha256: str|None = None

    def __init__(self,
                 abs_path: str|pl.Path|None = None,
                 rel_path: str|pl.Path|None = None,
                 rel_base: str|pl.Path|None = None,
                 md5: str|None = None, sha256: str|None = None
                ):
        self.abs_path = abs_path  #type: ignore
        self.rel_path = rel_path  #type: ignore
        self.rel_base = rel_base  #type: ignore
        self.md5 = md5
        self.sha256 = sha256

        self.__post_init__()
        return None

    def __str__(self) -> str:
        tmp = dict((k.strip("_"), v) for k, v in self.__dict__.items())
        return f"{tmp}"

    def __repr__(self) -> str:
        return self.__str__()

    def __post_init__(self):
        if self.abs_path is not None:
            self._set_file_size()
        elif self.rel_base is not None and self.rel_path is not None:
            self.abs_path = self.rel_base.joinpath(self.rel_path)
            self._set_file_size()
        elif self.rel_path is None:
            raise RuntimeError(
                "Cannot create file instance w/o abs_path or rel_path"
            )
        else:
            pass
        return None

    def _set_file_size(self):
        assert self.abs_path is not None
        if self.abs_path.is_file():
            finfo = os.stat(self.abs_path)
            file_size = finfo.st_size
            self.size = file_size
            self._exists = 1
        return None

    def _validate_hash(self, hash, fixed_length) -> None:
        if hash is None:
            pass
        elif isinstance(hash, str):
            has_length = len(hash)
            if has_length != fixed_length:
                raise ValueError(
                    f"Invalid hash length: {hash} / {has_length} != {fixed_length}"
                )
            mobj = re.match(f"^[a-z0-9]{{{fixed_length}}}$", hash, flags=re.IGNORECASE)
            if mobj is None:
                raise ValueError(f"Invalid characters in hash [a-z0-9]: {hash}")
        else:
            raise TypeError(f"Expected hash to be of type string, not: {type(hash)}")
        return None

    @property
    def abs_path(self) -> pl.Path|None:
        return self._abs_path

    @abs_path.setter
    def abs_path(self, path: str|pl.Path) -> None:
        try:
            self._abs_path = pl.Path(path).resolve()
        except TypeError:
            self._abs_path = None

    @property
    def rel_path(self) -> pl.Path|None:
        return self._rel_path

    @rel_path.setter
    def rel_path(self, path: str|pl.Path) -> None:
        try:
            self._rel_path = pl.Path(path)
        except TypeError:
            self._rel_path = None

    @property
    def rel_base(self) -> pl.Path|None:
        return self._rel_base

    @rel_base.setter
    def rel_base(self, path: str|pl.Path) -> None:
        try:
            self._rel_base = pl.Path(path)
        except TypeError:
            self._rel_base = None

    @property
    def size(self) -> int:
        assert self._size is not None
        return self._size.size

    @size.setter
    def size(self, value: int|str|float) -> None:
        try:
            self._size = FileSize(value)
        except TypeError:
            self._size = None

    @property
    def md5(self) -> str|None:
        return self._md5

    @md5.setter
    def md5(self, value: str|None) -> None:
        try:
            self._validate_hash(value, 32)
            self._md5 = value
        except Exception as err:
            err.add_note("md5")
            raise

    @property
    def sha256(self) -> str|None:
        return self._sha256

    @sha256.setter
    def sha256(self, value: str|None) -> None:
        try:
            self._validate_hash(value, 64)
            self._sha256 = value
        except Exception as err:
            err.add_note("sha256")
            raise

    def get_unit_size(self, unit: FileSizeUnit) -> int|float:
        return getattr(self._size, unit.name)

    def update(self):
        pass


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
