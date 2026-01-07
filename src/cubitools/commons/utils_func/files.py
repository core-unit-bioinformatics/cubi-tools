
import itertools as itt

def get_collected_files_iter(collected_files):
    return itt.chain.from_iterable(collected_files.values())
