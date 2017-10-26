from __future__ import print_function

from sys import stderr

from flask import Flask
from flask import Response
from flask import redirect
from flask import request
from flask import session
from flask import url_for

from oop import extend


# noinspection PyUnresolvedReferences
# from typing import KeysView


def reroute_to(route_func, *args, **kwargs):
    # type: (callable) -> Response
    """
    Wrap redirect(url_for(...)) for route.func_name.

    :param route_func: the route function to redirect to
    :return: the Response from redirect(url_for(route.func_name))
    """
    if args or kwargs:
        session.args = args
        session.kwargs = kwargs
    return redirect(url_for(route_func.func_name))


def bind_args(backup_route):
    # type: (callable) -> callable
    """
    Wrap a route that calls the original route
    with args and kwargs passed through the session.

    backup_route is the route rerouted to
    if the session doesn't contain args or kwargs.
    """

    def binder(route_func):
        @preconditions(backup_route, session_contains('args', 'kwargs'))
        def delegating_route():
            d = session.__dict__  # type: dict[str, any]
            return route_func(*d.pop('args'), **d.pop('kwargs'))

        return delegating_route

    return binder


@extend(Flask)
def reroute_from(app, rule, **options):
    # type: (Flask, str, dict[str, any]) -> callable
    """
    Redirect the given rule and options to the route it is decorating.

    :param app: this app
    :param rule: rule from @app.route
    :param options: options from @app.route
    :return: a decorator that adds the redirecting logic
    """

    def decorator(func_to_reroute):
        # type: (callable) -> callable
        """
        Decorate a route function to add another route that redirects to this one.

        :param func_to_reroute: the route function to redirect
        :return: the original func_to_redirect
        """

        def rerouter():
            # type: () -> Response
            """
            The actual route function that accomplishes the redirecting.

            :return: the redirected Response
            """
            return reroute_to(func_to_reroute)

        # uniquely modify the rerouter name
        # so @app.route will have a unique function name
        # the next time reroute_from is called
        rerouter.func_name += '_for_' + func_to_reroute.func_name
        app.route(rule, **options)(rerouter)

        return func_to_reroute

    return decorator


def _debug(obj):
    # type: (any) -> bool
    return hasattr(obj, 'debug') and obj.debug


def preconditions(backup_route, *precondition_funcs):
    # type: (callable, callable | None) -> callable
    """
    Assert that all the given precondition_funcs are True when a route is called.
    If any of them aren't, reroute to the given backup route.

    If the attribute .debug is True for any of the precondition funcs,
    an error message will printed in the console.

    :param backup_route: the backup route to reroute to if any preconditions aren't met
    :param precondition_funcs: the precondition functions that must be met
    :return: the decorated route
    """

    def decorator(route):
        # type: (callable) -> callable
        def debug(precondition):
            # type: (callable) -> None
            # noinspection PyTypeChecker
            if _debug(preconditions) or _debug(precondition):
                print('<{}> failed on precondition <{}>, '
                      'rerouting to backup <{}>'
                      .format(route.func_name,
                              precondition.func_name,
                              backup_route.func_name),
                      file=stderr)

        def rerouter():
            # type: () -> Response
            for precondition in precondition_funcs:
                if not precondition():
                    debug(precondition)
                    return reroute_to(backup_route)
            return route()

        rerouter.func_name = route.func_name
        return rerouter

    return decorator


preconditions.debug = True


def method_is(http_method):
    # type: (str) -> callable
    """Assert the route is using the given HTTP method."""
    http_method = http_method.lower()

    def precondition():
        # type: () -> bool
        return request.method.lower() == http_method

    return precondition


post_only = method_is('post')
post_only.debug = True


def methods_are(*http_methods):
    # type: (list[str]) -> callable
    """Assert the route is using one of the given HTTP methods."""
    http_methods = {http_method.lower() for http_method in http_methods}

    def precondition():
        # type: () -> bool
        return request.method.lower() in http_methods

    return precondition


def set_contains(set_, *values):
    # type: (set[T] | KeysView[T], list[T]) -> callable
    """Assert a set contains all the given values."""
    values = set(values)

    def precondition():
        # type: () -> bool
        # check if set contains all values (using subset)
        return values <= set_

    return precondition


def dict_contains(dictionary, keys, calling_func=None):
    # type: (dict[T, any] | KeyViewFuture, list[T], callable | None) -> callable
    """Assert a dict contains all the given keys."""
    keys = set(keys)

    def precondition():
        # type: () -> bool
        # check if set contains all values (using subset)
        return keys <= set(dictionary.viewkeys())

    precondition.debug = True

    if calling_func is not None:
        precondition.func_name = calling_func.func_name + repr(tuple(keys))

    return precondition


class KeyViewFuture(object):
    def __init__(self, dict_supplier):
        self.dict_supplier = dict_supplier

    def viewkeys(self):
        return self.dict_supplier().viewkeys()


def form_contains(*fields):
    # type: (list[str]) -> callable
    """Assert request.form contains all the given fields."""
    return dict_contains(KeyViewFuture(lambda: request.form), fields, form_contains)


def session_contains(*keys):
    # type: (list[any]) -> callable
    """Assert session contains all the given keys."""
    return dict_contains(session, keys, session_contains)


def has_attrs(obj, *attrs):
    # type: (any, list[str]) -> callable
    """Assert an object contains all the given fields/attributes."""
    return dict_contains(obj.__dict__, attrs, has_attrs)
