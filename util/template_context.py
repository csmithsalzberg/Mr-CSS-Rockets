import sys

from flask import Flask

context = sys.modules[__name__].__dict__  # type: dict[str, any]


def _filter_hidden(dictionary):
    # type: (dict[str, any]) -> dict[str, any]
    """Filters out any attribute starting with _, which are supposed to be hidden."""
    return {k: v for k, v in dictionary.viewitems() if not k.startswith('_')}


def _filter_hidden_obj(obj):
    return _filter_hidden({field: getattr(obj, field) for field in dir(obj)})


# add non-hidden builtins
context.update(_filter_hidden_obj(__builtins__))


def splat():
    # type: () -> dict[str, any]
    return context


def if_else(first, a, b):
    # type: (bool, any, any) -> any
    """
    Functional equivalent of conditional expression.

    :param first: True or False
    :param a: to be returned if first is True
    :param b: to be returned if first is False
    :return: a if first else b
    """
    return a if first else b


def repeat(s, n):
    # type: (str, int) -> str
    return s * n


def br(n):
    # type: (int) -> str
    """
    Concisely create many <br> tags.

    :param n: number of <br> to retur
    :return: n <br> tags
    """
    return repeat('<br>', n)


# remove hiddens
context = _filter_hidden(context)


def add_to(app):
    # type: (Flask) -> None
    for name, value in context.viewitems():
        app.add_template_global(value, name)


if __name__ == '__main__':
    from pprint import pprint

    pprint(context)
