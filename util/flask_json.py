from __future__ import print_function

from flask import Flask, sessions
from flask.json import JSONDecoder
from flask.json import JSONEncoder

from util.namedtuple_factory import all_namedtuples
from util.oop import override


def serialize_named_tuple(named_tuple):
    fields = named_tuple._asdict()
    fields['_type'] = repr(type(named_tuple))
    return fields


@override(sessions)
def _tag(_super, o):
    # type: (any) -> dict
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
        # type: (any) -> any
        if not hasattr(o, '_asdict'):
            return o
        fields = dict(o._asdict())
        fields['_type'] = repr(type(o))
        return fields

    def default(self, o):
        new_o = self.convert(o)
        if new_o is o:
            return super(NamedTupleJsonEncoder, self).default(o)
        return new_o


class NamedTupleJsonDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        kwargs['object_hook'] = NamedTupleJsonDecoder.object_hook
        super(NamedTupleJsonDecoder, self).__init__(*args, **kwargs)

    @staticmethod
    def object_hook(obj):
        print('object_hook:', obj)
        if '_type' not in obj:
            return obj
        o_type = obj.pop('_type')
        return all_namedtuples[o_type](**obj)


def use_named_tuple_json(app):
    # type: (Flask) -> None
    app.json_encoder = NamedTupleJsonEncoder
    app.json_decoder = NamedTupleJsonDecoder
    pass
