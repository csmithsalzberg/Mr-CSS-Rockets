import collections

from typing import List, NamedTuple, Dict

all_namedtuples = {}  # type: Dict[str, type(NamedTuple)]


def namedtuple(typename, field_names, verbose=False, rename=False):
    # type: (str, List[str]) -> type(NamedTuple)
    _type = collections.namedtuple(typename, field_names, verbose, rename)
    all_namedtuples[repr(_type)] = _type
    return _type
