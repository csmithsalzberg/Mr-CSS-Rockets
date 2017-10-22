from __future__ import print_function

from sys import stderr

from flask import Flask
from flask import Response
from flask import redirect
from flask import request
from flask import session
from flask import url_for

# noinspection PyUnresolvedReferences
import route_extension_methods
from oop import extend


def reroute_to(route_func):
    # type: (callable) -> Response
    """
    Wrap redirect(url_for(...)) for route.func_name.

    :param route_func: the route function to redirect to
    :return: the Response from redirect(url_for(route.func_name))
    """
    return redirect(url_for(route_func.func_name))


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


preconditions.debug = False


def post_only():
    # type: () -> bool
    """Assert the route is using POST."""
    return request.method.lower() == 'post'


def dict_contains(map, *keys):
    # type: (dict[T, any], list[T]) -> callable
    """Assert a dict contains all the given keys."""

    def precondition():
        # type: () -> bool
        # check if map contains all keys (using subset)
        return set(keys) <= map.viewkeys()

    return precondition


def form_contains(*fields):
    # type: (list[str]) -> callable
    """Assert request.form contains all the given fields."""
    return dict_contains(request.form, *fields)


def session_contains(*keys):
    # type: (list[any]) -> callable
    """Assert session contains all the given keys."""
    return dict_contains(session, *keys)
