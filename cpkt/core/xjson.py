import decimal
import functools
import json


@functools.singledispatch
def convert(o):
    _ = o
    raise TypeError('can not convert type')


@convert.register(decimal.Decimal)
def _(o):
    return str(o)


class ExtendJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return convert(obj)
        except TypeError:
            return super(ExtendJSONEncoder, self).default(obj)
