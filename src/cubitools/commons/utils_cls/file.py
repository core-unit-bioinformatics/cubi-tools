
import os
import pathlib as pl
import re

from cubitools.commons.enums import FileSizeUnit

from cubitools.commons.utils_cls.filesize import FileSize


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
