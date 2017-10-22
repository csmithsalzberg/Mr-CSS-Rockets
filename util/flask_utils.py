from __future__ import print_function

from collections import Iterable
from sys import stderr

import flask
from flask import Flask
from flask import Response
from flask import redirect
from flask import request
from flask import url_for

# noinspection PyUnresolvedReferences
import route_extension_methods
from default_template_context import get_default_template_context
from oop import extend, override


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


OVERRIDE_RENDER_TEMPLATE = False

if OVERRIDE_RENDER_TEMPLATE:
    @override(flask)
    def render_template(_super, template_name_or_list, **context):
        # type: (callable, str | Iterable[str], dict[str, any]) -> Response
        """
        Wrap flask.render_template to add default template args.

        :param _super: super method
        :param template_name_or_list: the template name(s)
        :param context: original context
        :return: the Response from flask.render_template
        """
        return _super(template_name_or_list,
                      **get_default_template_context(context))


def _debug(obj):
    # type: (any) -> bool
    return hasattr(obj, 'debug') and obj.debug


def preconditions(backup_route, *precondition_funcs):
    # type: (callable, callable | None) -> callable
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
    return request.method.lower() == 'post'
