
import collections as col
import math
import re
import sys

from cubitools.commons.enums import FileSizeUnit


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

    def __add__(self, other: 'int|float|FileSize') -> 'int|float|FileSize':
        # https://peps.python.org/pep-0484/
        if isinstance(other, int):
            return self.size + other
        elif isinstance(other, float):
            return self.size + other
        elif isinstance(other, FileSize):
            return FileSize(self.size + other.size)
        else:
            raise TypeError

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
