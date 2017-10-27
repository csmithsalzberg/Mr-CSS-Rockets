import collections

from typing import List, Union

all_namedtuples = {}


def namedtuple(typename, field_names, verbose=False, rename=False):
    # type: (str, List[str]) -> Union[tuple, callable]
    _type = collections.namedtuple(typename, field_names, verbose, rename)
    all_namedtuples[repr(_type)] = _type
    return _type
