import sys

context = sys.modules[__name__].__dict__  # type: dict[str, any]


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
