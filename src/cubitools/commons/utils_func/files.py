
import itertools as itt
import typing as typ

from cubitools.commons.utils_cls.file import File


def get_files_iter(files: dict[str, list[File]]) -> typ.Iterable[File]:
    """Convenience wrapper to iterate over all files
    [type File] when nested as a dict of lists.

    This function can be extended to return iterators for
    other nested input data structures as long as the output
    type does not change.

    Args:
        collected_files (dict[str, list[File]]): _description_

    Returns:
        _type_: _description_
    """
    if isinstance(files, dict):
        return itt.chain.from_iterable(files.values())
    else:
        raise TypeError(f"Cannot handle input structure of type: {type(files)}")
