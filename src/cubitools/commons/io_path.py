
import pathlib as pl


class IOPath:

    def __init__(self):
        return None

    @classmethod
    def input_file(cls, path):
        p = pl.Path(path).resolve(strict=True)
        if not p.is_file():
            raise TypeError(f"Input path is not a file: {path}")
        return p

    @classmethod
    def input_dir(cls, path):
        p = pl.Path(path).resolve(strict=True)
        if not p.is_dir():
            raise TypeError(f"Input path is not a directory: {path}")
        return p

    @classmethod
    def output_file(cls, path):
        p = pl.Path(path).resolve(strict=False)
        if p.is_dir():
            raise TypeError(f"Output path points to directory: {path}")
        return p

    @classmethod
    def output_dir(cls, path):
        p = pl.Path(path).resolve(strict=False)
        if p.is_file():
            raise TypeError(f"Output path points to file: {path}")
        return p
