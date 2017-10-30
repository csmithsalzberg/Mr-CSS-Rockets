from __future__ import print_function

from flask import Flask, sessions
from flask.json import JSONDecoder
from flask.json import JSONEncoder
from typing import Callable, Any, Dict, NamedTuple, Union

from util.namedtuple_factory import all_namedtuples
from util.oop import override


def serialize_named_tuple(named_tuple):
    # type: (NamedTuple) -> Dict[str, Any]
    fields = named_tuple._asdict()
    fields['_type'] = repr(type(named_tuple))
    return fields


@override(sessions)
def _tag(_super, o):
    # type: (Callable[Any, Any]) -> Dict[str, Any] | Any
    if hasattr(o, '_asdict'):
        return serialize_named_tuple(o)
    return _super(o)


class NamedTupleJsonEncoder(JSONEncoder):
    def iterencode(self, o, _one_shot=False):
        chunks = super(NamedTupleJsonEncoder, self).iterencode(o, _one_shot)
        for chunk in chunks:
            yield self.convert(chunk)

    @staticmethod
    def convert(o):
        # type: (Any) -> Dict[str, Any] | Any
        if not hasattr(o, '_asdict'):
            return o
        fields = dict(o._asdict())
        fields['_type'] = repr(type(o))
        return fields

    def default(self, o):
        # type: (Any) -> Dict[str, Any]
        new_o = self.convert(o)
        if new_o is o:
            return super(NamedTupleJsonEncoder, self).default(o)
        return new_o


class NamedTupleJsonDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        kwargs['object_hook'] = NamedTupleJsonDecoder.make_object_hook(
            kwargs.get('object_hook', None))
        super(NamedTupleJsonDecoder, self).__init__(*args, **kwargs)

    @staticmethod
    def make_object_hook(_super):
        def object_hook(obj):
            # type: (Any) -> Union[NamedTuple, Any]
            if '_type' not in obj:
                if _super is None:
                    return obj
                else:
                    return _super(obj)
            return all_namedtuples[obj.pop('_type')](**obj)
        return object_hook


def use_named_tuple_json(app):
    # type: (Flask) -> None
    app.json_encoder = NamedTupleJsonEncoder
    app.json_decoder = NamedTupleJsonDecoder
