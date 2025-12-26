
import collections as col
import math
import re

from cubitools.commons.enums import FileSizeUnit



FilePath = col.namedtuple(
    "FilePath",
    field_names=["full_path", "relative_path", "path_type", "file_size"]
)


class FileSize:

    __slots__ = ["size"] + [FileSizeUnit(i).name for i in range(len(FileSizeUnit))]

    def __init__(self, file_size):
        if isinstance(file_size, str):
            self.size = self._string_to_byte(file_size)
        elif isinstance(file_size, int):
            self.size = file_size
        elif isinstance(file_size, float):
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
