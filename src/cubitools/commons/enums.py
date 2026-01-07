
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
    GZIP = 0
    XZ = 1


class Checksum(enum.Enum):
    MD5 = 0
    SHA1 = 1
    SHA256 = 2
