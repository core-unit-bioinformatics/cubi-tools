
import dataclasses
import enum


class FileSizeUnit(enum.Enum):
    b = 0
    byte = 0
    kb = 1
    k = 1
    mb = 2
    m = 2
    gb = 3
    g = 3
    tb = 4
    t = 4


class FileManifestType(enum.Enum):
    complete = 0
    minimal = 1
    coreutils = 2
    skip = 3


class PathType(enum.Enum):
    regular = 0
    hidden = 1
    symbolic = 2


class PathComponent(enum.Enum):
    filename = 0
    absolute = 1
    relative = 2
    parent = 3


class Compression(enum.Enum):
    gz = 0
    gzip = 0
    xz = 1


class Checksum(enum.Enum):
    md5 = 0
    sha1 = 1
    sha256 = 2


@dataclasses.dataclass(frozen=True)
class ChecksumLength:
    md5: int = 32
    sha1: int = 40
    sha256: int = 64

    @classmethod
    def get_length_order(cls):
        """get_length_order
        """
        ordered = sorted(
            [(f.default, f.name) for f in dataclasses.fields(cls)]
        )
        return ordered


class GitAuth(enum.Enum):
    ssh = 0
    https = 1
