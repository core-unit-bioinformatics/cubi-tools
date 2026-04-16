
import argparse as argp
import pathlib as pl


class IOPath:

    def __init__(self):
        return None

    @classmethod
    def input_file(cls, path):
        p = pl.Path(path).resolve(strict=True)
        if not p.is_file():
            raise argp.ArgumentTypeError(f"Input path is not a file: {path}")
        return p

    @classmethod
    def input_dir(cls, path):
        p = pl.Path(path).resolve(strict=True)
        if not p.is_dir():
            raise argp.ArgumentTypeError(f"Input path is not a directory: {path}")
        return p

    @classmethod
    def output_file(cls, path):
        p = pl.Path(path).resolve(strict=False)
        if p.is_dir():
            raise argp.ArgumentTypeError(f"Output path points to existing directory: {path}")
        return p

    @classmethod
    def output_dir(cls, path):
        p = pl.Path(path).resolve(strict=False)
        if p.is_file():
            raise argp.ArgumentTypeError(f"Output path points to existing file: {path}")
        return p

    @classmethod
    def output_prefix(cls, path):
        p = pl.Path(path.strip(".")).resolve(strict=False)
        if p.is_dir():
            err_msg = (
                f"Output path prefix points to existing directory: {path} --- "
                "An output path prefix specifies a file prefix for output files. "
                "It must thus be a combination of a directory plus a prefix or simply "
                "a prefix, which implies a file creation in the current working directory."
            )
            raise argp.ArgumentTypeError(err_msg)
        return p

