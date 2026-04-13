
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


class PathType(enum.Enum):
    REGULAR = 0
    HIDDEN = 1
    SYMBOLIC = 2


class Compression(enum.Enum):
    gzip = 0
    gz = 0
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
