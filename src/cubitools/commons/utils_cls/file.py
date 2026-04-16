
import os
import pathlib as pl
import re

from cubitools.commons.enums import FileSizeUnit, Checksum, ChecksumLength, \
    FileManifestType, PathComponent

from cubitools.commons.utils_cls.filesize import FileSize


class File:
    _abs_path: pl.Path|None = None
    _rel_path: pl.Path|None = None
    _rel_base: pl.Path|None = None
    _exists: int|None = None
    _size: FileSize|None = None
    _md5: str|None = None
    _sha1: str|None = None
    _sha256: str|None = None

    def __init__(self,
                 abs_path: str|pl.Path|None = None,
                 rel_path: str|pl.Path|None = None,
                 rel_base: str|pl.Path|None = None,
                 md5: str|None = None,
                 sha1: str|None = None,
                 sha256: str|None = None
                ):
        self.abs_path = abs_path  #type: ignore
        self.rel_path = rel_path  #type: ignore
        self.rel_base = rel_base  #type: ignore
        self.md5 = md5
        self.sha1 = sha1
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
        """Set the file size attribute (size in bye) if the file exists.
        Note that this function is called in the __post_init__ function,
        which ensures that abs_path is set.

        Returns:
            _type_: _description_
        """
        assert self.abs_path is not None
        if self.abs_path.is_file():
            finfo = os.stat(self.abs_path)
            file_size = finfo.st_size
            self.size = file_size
            self._exists = 1
        else:
            self._exists = 0
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
            self._abs_path = pl.Path(path).resolve(strict=False)
            if self._abs_path.is_file():
                self._exists = 1
            else:
                self._exists = 0
            if self.rel_base is not None:
                assert self.abs_path is not None  # calm pylint...
                self.rel_path = self.abs_path.relative_to(self.rel_base)
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
            self._validate_hash(value, ChecksumLength.md5)
            self._md5 = value
        except Exception as err:
            err.add_note(Checksum.md5.name)
            raise

    @property
    def sha1(self) -> str|None:
        return self._sha1

    @sha1.setter
    def sha1(self, value: str|None) -> None:
        try:
            self._validate_hash(value, ChecksumLength.sha1)
            self._sha1 = value
        except Exception as err:
            err.add_note(Checksum.sha1.name)
            raise

    @property
    def sha256(self) -> str|None:
        return self._sha256

    @sha256.setter
    def sha256(self, value: str|None) -> None:
        try:
            self._validate_hash(value, ChecksumLength.sha256)
            self._sha256 = value
        except Exception as err:
            err.add_note(Checksum.sha256.name)
            raise

    def get_unit_size(self, unit: FileSizeUnit) -> int|float:
        return getattr(self._size, unit.name)

    def update(self):
        pass

    def delete(self):
        """Delete this file from the file system.
        This sets this _exists member to 0 if the operation
        succeeds or if a FileNotFoundError is raised.
        If an IOError is raised, the _exists member is set to None
        to indicate an unknown state.
        As a side effect, the absolute path is set in case that
        only the relative base and path are set.
        """
        try:
            if self.abs_path is not None:
                os.unlink(self.abs_path)
            elif self.rel_base is not None and self.rel_path is not None:
                abs_path = self.rel_base.joinpath(self.rel_path)
                os.unlink(abs_path)
                self.abs_path = abs_path
            else:
                self._exists = None
        except FileNotFoundError:
            self._exists = 0
        except IOError:
            self._exists = None
        return

    def get_fofn_entry(self, path_info=PathComponent.filename) -> str:
        """get_fofn_entry _summary_

        Args:
            path_info (_type_, optional): _description_. Defaults to None.
        """
        try:
            path_info = PathComponent[path_info]  # type: ignore
        except KeyError:
            path_info = PathComponent(path_info)

        fofn_entry = None
        if path_info == PathComponent.filename:
            if self.abs_path is not None:
                fofn_entry = self.abs_path.name
            elif self.rel_path is not None:
                fofn_entry = self.rel_path.name
            else:
                raise ValueError(f"Incomplete file record: {self}")
        elif path_info == PathComponent.absolute:
            assert self.abs_path is not None
            fofn_entry = self.abs_path
        elif path_info == PathComponent.relative:
            assert self.rel_path is not None
            fofn_entry = self.rel_path
        else:
            assert self.rel_base is not None
            assert self.rel_path is not None
            self_parent = self.rel_base.name
            rel_parent = pl.Path(self_parent).joinpath(self.rel_path)
            fofn_entry = rel_parent
        return str(fofn_entry)

    def get_manifest_line(self, manifest_type):
        """get_manifest_line _summary_

        Args:
            manifest_type (_type_): _description_
        """
        try:
            manifest_type = FileManifestType[manifest_type]  # type: ignore
        except KeyError:
            manifest_type = FileManifestType(manifest_type)

        header = []
        row = []
        if manifest_type == FileManifestType.minimal:
            header.append("filename")
            path_entry = self.get_fofn_entry()
        elif manifest_type == FileManifestType.complete:
            header.append("filepath")
            path_entry = self.get_fofn_entry(PathComponent.parent)
        else:
            raise RuntimeError(f"Unknown manifest type: {manifest_type}")
        row.append(path_entry)
        header.append("size")
        row.append(str(self.size))

        known_checksums = ChecksumLength.get_length_order()

        for length, name in known_checksums:
            try:
                checksum = getattr(self, name)
            except AttributeError:
                continue
            else:
                if checksum is None:
                    checksum = "n/a"
                if manifest_type == FileManifestType.complete:
                    header.append(name)
                    row.append(checksum)
                elif manifest_type == FileManifestType.minimal and checksum != "n/a":
                    header.append(name)
                    row.append(checksum)
                    break
                else:
                    continue

        return tuple(header), tuple(row)
